import { use } from 'react';

import { ThemeContext } from './ThemeContext';

// Current theme and setTheme('light' | 'dark'), in any component inside ThemeProvider
export function useTheme() {
  const context = use(ThemeContext);
  if (!context) throw new Error('useTheme must be used inside ThemeProvider');
  return context;
}
