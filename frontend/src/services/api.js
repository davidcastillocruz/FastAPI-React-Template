import axios from "axios";

/**
 * Shared Axios instance.
 *
 * - Base URL comes from `VITE_API_URL` so it can differ per environment.
 * - `withCredentials` is required so the backend receives the
 *   `language` cookie used for i18n.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 15000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

export default api;