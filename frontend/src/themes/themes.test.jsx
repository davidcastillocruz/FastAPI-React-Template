import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { setSystemDark } from '@/test/matchMedia';
import { getCookie, setCookie } from '@/utils/cookies';

import { applyTheme, getInitialTheme, getSavedTheme } from './themes';
import ThemeProvider from './ThemeProvider';
import { useTheme } from './useTheme';

function ThemeButtons() {
  const { theme, setTheme } = useTheme();
  return (
    <>
      <p>Theme: {theme}</p>
      <button onClick={() => setTheme('dark')}>dark</button>
      <button onClick={() => setTheme('purple')}>purple</button>
    </>
  );
}

function renderTheme() {
  return render(
    <ThemeProvider>
      <ThemeButtons />
    </ThemeProvider>,
  );
}

const html = document.documentElement;

// A failed expect never reaches the end of its test: the spies are restored here
afterEach(() => vi.restoreAllMocks());

describe('theme detection', () => {
  test('without a cookie it follows the system', () => {
    expect(getInitialTheme()).toBe('light');
    setSystemDark(true);
    expect(getInitialTheme()).toBe('dark');
  });

  test('a valid cookie wins over the system', () => {
    setCookie('theme', 'light');
    setSystemDark(true);
    expect(getInitialTheme()).toBe('light');
  });

  test('an invalid cookie is deleted', () => {
    setCookie('theme', 'purple');
    expect(getSavedTheme()).toBeNull();
    expect(getCookie('theme')).toBeNull();
  });

  test('applyTheme sets the attribute of the variables and the color scheme', () => {
    applyTheme('dark');
    expect(html.dataset.theme).toBe('dark');
    expect(html.style.colorScheme).toBe('dark');
  });
});

describe('ThemeProvider', () => {
  test('applies the theme to <html>', () => {
    setSystemDark(true);
    renderTheme();
    expect(screen.getByText('Theme: dark')).toBeTruthy();
    expect(html.dataset.theme).toBe('dark');
  });

  test('setTheme saves the cookie and applies the theme', () => {
    renderTheme();
    act(() => screen.getByRole('button', { name: 'dark' }).click());
    expect(html.dataset.theme).toBe('dark');
    expect(getCookie('theme')).toBe('dark');
  });

  test('an unknown theme is ignored', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    renderTheme();
    act(() => screen.getByRole('button', { name: 'purple' }).click());
    expect(html.dataset.theme).toBe('light');
    expect(getCookie('theme')).toBeNull();
    expect(error).toHaveBeenCalledOnce();
  });

  test('follows the system live while the user has not picked a theme', () => {
    renderTheme();
    act(() => setSystemDark(true));
    expect(html.dataset.theme).toBe('dark');
  });

  test('a picked theme wins over a change of the system', () => {
    renderTheme();
    act(() => screen.getByRole('button', { name: 'dark' }).click());
    // A real change, to dark and back to light
    act(() => setSystemDark(true));
    act(() => setSystemDark(false));
    expect(html.dataset.theme).toBe('dark');
  });

  test('useTheme outside the provider fails with a clear error', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<ThemeButtons />)).toThrow('useTheme must be used inside ThemeProvider');
  });
});
