import { useCallback } from 'react';

import { LANGUAGES, MAIN_LANGUAGE } from './languages';
import { useLanguage } from './useLanguage';

// "Hello {name}": {name} is filled with t("greeting", { name: "Ana" })
const PLACEHOLDER = /\{(\w+)\}/g;

// Translation files already checked, each one only the first time it's used
const checked = new WeakSet();

function placeholdersOf(text) {
  return [...text.matchAll(PLACEHOLDER)]
    .map((match) => match[1])
    .sort()
    .join(', ');
}

// Development only: every key has a text in every language, with the same {placeholders}
function checkTranslations(translations) {
  if (!import.meta.env.DEV || checked.has(translations)) return;
  checked.add(translations);

  for (const [key, texts] of Object.entries(translations)) {
    const missing = LANGUAGES.filter((language) => typeof texts?.[language] !== 'string');
    if (missing.length) {
      console.error(`Translation "${key}" has no text in: ${missing.join(', ')}`, texts);
      continue;
    }
    const expected = placeholdersOf(texts[MAIN_LANGUAGE]);
    for (const language of LANGUAGES) {
      if (placeholdersOf(texts[language]) !== expected) {
        console.error(`Translation "${key}" has different {placeholders} in "${language}"`, texts);
      }
    }
  }
}

// t(key, args) for the texts of a component, in the current language:
//   const t = useT(translations)   (translations: the component's *Translation.json)
//   t('title')  t('greeting', { name: 'Ana' })
// A missing text falls back to the main language, a missing key shows the key itself
export function useT(translations) {
  const { language } = useLanguage();
  checkTranslations(translations);

  return useCallback(
    (key, args = {}) => {
      const texts = translations[key];
      if (!texts) {
        console.error(`Translation "${key}" not found`);
        return key;
      }
      const text = texts[language] ?? texts[MAIN_LANGUAGE];
      if (typeof text !== 'string') return key;
      return text.replace(PLACEHOLDER, (match, name) => (Object.hasOwn(args, name) ? String(args[name]) : match));
    },
    [translations, language],
  );
}
