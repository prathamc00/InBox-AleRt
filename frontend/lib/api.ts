import axios from "axios";

// Use same-origin proxy by default to avoid browser CORS/mixed-content/network issues.
// Set NEXT_PUBLIC_API_URL only when you explicitly want direct browser-to-backend calls.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const FALLBACK_LOCAL_API_URL = "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    // If proxy-based request fails at network layer, retry once directly to local backend.
    if (!error.response && original && !original._networkRetry) {
      original._networkRetry = true;
      const currentBase = original.baseURL ?? API_URL;
      if (currentBase === "/backend") {
        original.baseURL = FALLBACK_LOCAL_API_URL;
        return api(original);
      }
    }

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = localStorage.getItem("refresh_token");
        if (!refresh) throw new Error("no refresh token");
        const { data } = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refresh });
        localStorage.setItem("access_token", data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        localStorage.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Settings types ────────────────────────────────────────────────────────────

export interface UserSettings {
  whatsapp_number: string | null;
  whatsapp_verified: boolean;
  notify_on_all: boolean;
  notify_daily_digest: boolean;
}

export interface UserSettingsPatch {
  whatsapp_number?: string | null;
  notify_on_all?: boolean;
  notify_daily_digest?: boolean;
}

// ── Auto-reply types ──────────────────────────────────────────────────────────

export interface AutoReplyConfig {
  is_enabled: boolean;
  dry_run: boolean;
  min_importance_score: number;
  reply_tone: "professional" | "friendly" | "brief";
  daily_auto_reply_limit: number;
  cancel_window_seconds: number;
  business_hours_only: boolean;
  business_hours_start: string;
  business_hours_end: string;
  timezone: string;
}
