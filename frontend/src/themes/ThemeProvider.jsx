import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react';

import { setCookie } from '@/utils/cookies';

import { ThemeContext } from './ThemeContext';
import { THEME_COOKIE, THEMES, applyTheme, getSavedTheme, getSystemTheme, systemDarkQuery } from './themes';

// The theme of the user if they picked one, the one of the system otherwise
export default function ThemeProvider({ children }) {
  const [savedTheme, setSavedTheme] = useState(getSavedTheme);
  const [systemTheme, setSystemTheme] = useState(getSystemTheme);
  const theme = savedTheme ?? systemTheme;

  // Follows the system live: only visible while the user hasn't picked a theme
  useEffect(() => {
    const onChange = () => setSystemTheme(getSystemTheme());
    systemDarkQuery.addEventListener('change', onChange);
    return () => systemDarkQuery.removeEventListener('change', onChange);
  }, []);

  // Layout effect: applied before the browser paints, no flash of the old theme
  useLayoutEffect(() => applyTheme(theme), [theme]);

  const setTheme = useCallback((next) => {
    if (!THEMES.includes(next)) {
      console.error(`Unknown theme "${next}", expected one of: ${THEMES.join(', ')}`);
      return;
    }
    setCookie(THEME_COOKIE, next);
    setSavedTheme(next);
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);

  return <ThemeContext value={value}>{children}</ThemeContext>;
}
