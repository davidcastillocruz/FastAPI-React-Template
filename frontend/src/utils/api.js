import axios from 'axios';

// Address of the backend: VITE_API_URL, written into the code when it's built, and checked by vite.config.js
export const API_URL = import.meta.env.VITE_API_URL;

// Every call to the backend: await api.get('/email-requests'), await api.post('/email-requests', { email })
// Errors: error.response.data.detail is the backend's message, already translated,
// no error.response means the backend didn't answer (down, or slower than the timeout)
export const api = axios.create({
  baseURL: API_URL,
  // A backend that hangs fails the request instead of leaving it waiting forever
  timeout: 10_000,
  // Sends the cookies (language...) to the backend
  withCredentials: true,
});
