import { use } from 'react';

import { LanguageContext } from './LanguageContext';

// Current language and setLanguage('en' | 'es'), in any component inside LanguageProvider
export function useLanguage() {
  const context = use(LanguageContext);
  if (!context) throw new Error('useLanguage must be used inside LanguageProvider');
  return context;
}
