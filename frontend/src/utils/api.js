import axios from 'axios';

// Every call to the backend: await api.get('/email-requests'), await api.post('/email-requests', { email })
// Errors: error.response.data.detail is the backend's message, already translated,
// no error.response means the backend didn't answer (down, or slower than the timeout)
export const api = axios.create({
  baseURL: 'http://localhost:8000',
  // A backend that hangs fails the request instead of leaving it waiting forever
  timeout: 10_000,
  // Sends the cookies (language...) to the backend
  withCredentials: true,
});
