import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// The address of the backend, without a / at the end: the paths of the calls start with one
const API_URL_FORMAT = /^https?:\/\/[^/\s]+(\/[^\s]*[^/\s])?$/;

// The settings of the frontend, from the environment: all of them required, like the ones of the backend.
// A missing or wrong one stops the server, the build and the tests here, not in the middle of a page
function checkSettings(mode) {
  const { VITE_API_URL: apiUrl } = loadEnv(mode, process.cwd(), 'VITE_');
  if (!API_URL_FORMAT.test(apiUrl || '')) {
    throw new Error(`VITE_API_URL must be the address of the backend, like http://localhost:8000 (it is "${apiUrl}")`);
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  checkSettings(mode);
  return {
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
  };
});
