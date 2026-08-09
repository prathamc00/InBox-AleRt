import axios from "axios";

const isBrowser = typeof window !== "undefined";
const isHttps = isBrowser && window.location.protocol === "https:";

// When running on HTTPS in browser (Vercel), force /backend proxy to avoid Mixed Content blocking
const API_URL = isHttps
  ? "/backend"
  : process.env.NEXT_PUBLIC_API_URL ?? "http://52.207.228.73:8000";
const FALLBACK_LOCAL_API_URL = "http://52.207.228.73:8000";




export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Helper: returns true when the current session is a demo session
const isDemoSession = () =>
  typeof window !== "undefined" &&
  localStorage.getItem("access_token")?.startsWith("demo-");

// Attach access token to every request
// Demo requests are short-circuited — they never reach the backend.
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    // Demo session: reject the request immediately with a synthetic response
    // so the dashboard shows empty/fallback state without hitting the server.
    if (token?.startsWith("demo-")) {
      return Promise.reject({
        isDemoShortCircuit: true,
        config,
        response: { status: 200, data: [], headers: {}, config },
      });
    }
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    // Demo short-circuit: resolve with an empty array so pages show fallback UI
    if (error?.isDemoShortCircuit) {
      return { ...error.response, data: Array.isArray(error.response?.data) ? [] : {} };
    }

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
        // Never attempt a real token refresh for demo sessions
        if (isDemoSession()) throw new Error("demo session");
        const refresh = localStorage.getItem("refresh_token");
        if (!refresh) throw new Error("no refresh token");
        const { data } = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refresh });
        localStorage.setItem("access_token", data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        // Only wipe auth & redirect for real (non-demo) sessions
        if (!isDemoSession()) {
          localStorage.clear();
          window.location.href = "/login";
        }
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
