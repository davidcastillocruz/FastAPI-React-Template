import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { getCookie, setCookie } from '@/utils/cookies';

import { LANGUAGES, MAIN_LANGUAGE, getBrowserLanguage, getInitialLanguage, getSavedLanguage } from './languages';
import LanguageProvider from './LanguageProvider';
import { useLanguage } from './useLanguage';
import { useT } from './useT';

// The tests follow the configured languages: changing MAIN_LANGUAGE or LANGUAGES doesn't break them
const MAIN = MAIN_LANGUAGE;
const OTHER = LANGUAGES.find((language) => language !== MAIN);
const UNKNOWN = 'xx';

// Languages of the browser for one test
function browserLanguages(...tags) {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(tags);
}

afterEach(() => vi.restoreAllMocks());

describe('language detection', () => {
  test('first language of the browser that the app has, trying the base one too', () => {
    browserLanguages(`${UNKNOWN}-YY`, `${OTHER}-YY`, MAIN);
    expect(getBrowserLanguage()).toBe(OTHER);
  });

  test('a browser without any of the app languages gets the main one', () => {
    browserLanguages(`${UNKNOWN}-YY`, 'zz');
    expect(getBrowserLanguage()).toBe(MAIN);
  });

  test('a valid cookie wins over the browser', () => {
    browserLanguages(MAIN);
    setCookie('language', OTHER);
    expect(getInitialLanguage()).toBe(OTHER);
  });

  test('an invalid cookie is deleted', () => {
    setCookie('language', UNKNOWN);
    expect(getSavedLanguage()).toBeNull();
    expect(getCookie('language')).toBeNull();
  });
});

// Each test gets its own translations: useT checks every file only the first time it sees it
function Texts({ translations, keyName = 'greeting', args = { name: 'Ana' } }) {
  const t = useT(translations);
  const { setLanguage } = useLanguage();
  return (
    <>
      <p>{t(keyName, args)}</p>
      <button onClick={() => setLanguage(OTHER)}>other</button>
      <button onClick={() => setLanguage(UNKNOWN)}>unknown</button>
    </>
  );
}

function renderTexts(props) {
  return render(
    <LanguageProvider>
      <Texts {...props} />
    </LanguageProvider>,
  );
}

// "en: Hello {name}", "es: Hello {name}"... one text per configured language
const greeting = () => ({
  greeting: Object.fromEntries(LANGUAGES.map((language) => [language, `${language}: Hello {name}`])),
});

describe('LanguageProvider and useT', () => {
  test('texts in the detected language, with the placeholders filled', () => {
    browserLanguages(OTHER);
    renderTexts({ translations: greeting() });
    expect(screen.getByText(`${OTHER}: Hello Ana`)).toBeTruthy();
    expect(document.documentElement.lang).toBe(OTHER);
  });

  test('setLanguage repaints the texts, saves the cookie and sets <html lang>', () => {
    browserLanguages(MAIN);
    renderTexts({ translations: greeting() });
    expect(screen.getByText(`${MAIN}: Hello Ana`)).toBeTruthy();

    act(() => screen.getByRole('button', { name: 'other' }).click());
    expect(screen.getByText(`${OTHER}: Hello Ana`)).toBeTruthy();
    expect(getCookie('language')).toBe(OTHER);
    expect(document.documentElement.lang).toBe(OTHER);
  });

  test('an unknown language is ignored', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    browserLanguages(MAIN);
    renderTexts({ translations: greeting() });
    act(() => screen.getByRole('button', { name: 'unknown' }).click());
    expect(screen.getByText(`${MAIN}: Hello Ana`)).toBeTruthy();
    expect(getCookie('language')).toBeNull();
    expect(error).toHaveBeenCalledOnce();
  });

  test('a missing placeholder argument stays as it is', () => {
    browserLanguages(MAIN);
    renderTexts({ translations: greeting(), args: {} });
    expect(screen.getByText(`${MAIN}: Hello {name}`)).toBeTruthy();
  });

  test('a missing key shows the key and logs an error', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    browserLanguages(MAIN);
    renderTexts({ translations: greeting(), keyName: 'nope' });
    expect(screen.getByText('nope')).toBeTruthy();
    expect(error).toHaveBeenCalledWith('Translation "nope" not found');
  });

  test('a missing text falls back to the main language and the file check reports it', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    browserLanguages(OTHER);
    renderTexts({ translations: { greeting: { [MAIN]: 'Hello {name}' } } });
    expect(screen.getByText('Hello Ana')).toBeTruthy();
    const missing = LANGUAGES.filter((language) => language !== MAIN).join(', ');
    expect(error).toHaveBeenCalledWith(`Translation "greeting" has no text in: ${missing}`, expect.anything());
  });

  test('the file check reports different placeholders between languages', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    browserLanguages(MAIN);
    renderTexts({ translations: { greeting: { ...greeting().greeting, [OTHER]: 'Hola {nombre}' } } });
    expect(error).toHaveBeenCalledWith(`Translation "greeting" has different {placeholders} in "${OTHER}"`, expect.anything());
  });

  test('useLanguage outside the provider fails with a clear error', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<Texts translations={greeting()} />)).toThrow('useLanguage must be used inside LanguageProvider');
  });
});
