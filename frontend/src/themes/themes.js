import { deleteCookie, getCookie } from '@/utils/cookies';

export const THEMES = ['light', 'dark'];
export const THEME_COOKIE = 'theme';

// Dark mode of the operating system, it can change while the page is open
export const systemDarkQuery = window.matchMedia('(prefers-color-scheme: dark)');

export function getSystemTheme() {
  return systemDarkQuery.matches ? 'dark' : 'light';
}

// Theme picked by the user, null if there's none. An invalid cookie ("theme=purple") is deleted
export function getSavedTheme() {
  const saved = getCookie(THEME_COOKIE);
  if (saved === null) return null;
  if (THEMES.includes(saved)) return saved;
  deleteCookie(THEME_COOKIE);
  return null;
}

export function getInitialTheme() {
  return getSavedTheme() ?? getSystemTheme();
}

// <html data-theme="dark"> turns on the variables of themes.css,
// color-scheme does the same for the browser's own parts (scrollbars, inputs...)
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}
