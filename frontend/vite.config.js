import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // "@/components/Button" -> "src/components/Button"
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // A fake browser (document, cookies...) for the tests, setup.js resets it after each one
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
  },
});
