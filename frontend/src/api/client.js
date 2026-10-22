import axios from "axios";

export const TOKEN_KEY = "claimflow_token";

const rawBaseUrl = import.meta.env.VITE_API_URL;
const baseURL =
  typeof rawBaseUrl === "string" && rawBaseUrl.trim() !== ""
    ? rawBaseUrl.trim().replace(/\/+$/, "")
    : "http://localhost:8000";

const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    const isAuthCall =
      error.config?.url?.startsWith("/api/auth/login") ||
      error.config?.url?.startsWith("/api/auth/register");
    if (error.response?.status === 401 && !isAuthCall) {
      localStorage.removeItem(TOKEN_KEY);
      if (!["/login", "/register", "/"].includes(window.location.pathname))
        window.location.assign("/login");
    }
    return Promise.reject(error);
  }
);

/** Turn any axios error into a message that is safe and readable for the user. */
export function errorMessage(error, fallback = "Something went wrong. Please try again.") {
  if (!error.response) {
    if (import.meta.env.DEV && baseURL.includes("localhost")) {
      return "Cannot reach the server. Is the backend running on port 8000?";
    }
    return "Cannot reach the server. Please verify your connection or try again in a few moments.";
  }
  const d = error.response.data?.detail;
  return typeof d === "string" ? d : fallback;
}

export async function downloadDocument(doc) {
  const res = await api.get(`/api/documents/${doc.id}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = doc.original_filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default api;
