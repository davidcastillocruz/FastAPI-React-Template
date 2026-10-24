import { deleteCookie, getCookie } from '@/utils/cookies';

// Same languages and cookie as the backend: the API answers in the language of the web
export const LANGUAGES = ['en', 'es'];
export const MAIN_LANGUAGE = 'en';
export const LANGUAGE_COOKIE = 'language';

// Language picked by the user, null if there's none. An invalid cookie ("language=fr") is deleted
export function getSavedLanguage() {
  const saved = getCookie(LANGUAGE_COOKIE);
  if (saved === null) return null;
  if (LANGUAGES.includes(saved)) return saved;
  deleteCookie(LANGUAGE_COOKIE);
  return null;
}

// First language of the browser that the app has, trying the base one too ("es-ES" -> "es")
export function getBrowserLanguage() {
  const tags = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const tag of tags) {
    const lower = (tag ?? '').toLowerCase();
    for (const option of [lower, lower.split('-')[0]]) {
      if (LANGUAGES.includes(option)) return option;
    }
  }
  return MAIN_LANGUAGE;
}

export function getInitialLanguage() {
  return getSavedLanguage() ?? getBrowserLanguage();
}
