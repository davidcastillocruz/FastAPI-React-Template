import { useCallback, useLayoutEffect, useMemo, useState } from 'react';

import { setCookie } from '@/utils/cookies';

import { LanguageContext } from './LanguageContext';
import { LANGUAGE_COOKIE, LANGUAGES, getInitialLanguage } from './languages';

// The language of the user if they picked one, the one of the browser otherwise.
// Changing it repaints every text, without reloading the page
export default function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(getInitialLanguage);

  // <html lang>: screen readers, the browser's spell checker and translator use it
  useLayoutEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback((next) => {
    if (!LANGUAGES.includes(next)) {
      console.error(`Unknown language "${next}", expected one of: ${LANGUAGES.join(', ')}`);
      return;
    }
    setCookie(LANGUAGE_COOKIE, next);
    setLanguageState(next);
  }, []);

  const value = useMemo(() => ({ language, setLanguage }), [language, setLanguage]);

  return <LanguageContext value={value}>{children}</LanguageContext>;
}
