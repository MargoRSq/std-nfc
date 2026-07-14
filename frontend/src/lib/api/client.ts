import axios, { type AxiosError } from "axios";
import { useAuthStore } from "@/stores/authStore";

export const apiClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

const AUTH_NO_RETRY = /\/auth\/(login|totp|recovery|refresh|password)/;

apiClient.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config!;
    const url = original.url ?? "";
    if (error.response?.status !== 401 || (original as unknown as Record<string, unknown>)["_retry"]) {
      return Promise.reject(error);
    }
    if (AUTH_NO_RETRY.test(url)) {
      return Promise.reject(error);
    }
    (original as unknown as Record<string, unknown>)["_retry"] = true;
    refreshing ||= refreshAccessToken();
    const newToken = await refreshing;
    refreshing = null;
    if (!newToken) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
      return Promise.reject(error);
    }
    original.headers!.Authorization = `Bearer ${newToken}`;
    return apiClient(original);
  },
);

async function refreshAccessToken(): Promise<string | null> {
  try {
    const refresh = useAuthStore.getState().refreshToken;
    if (!refresh) return null;
    const r = await axios.post("/api/auth/refresh", { refresh_token: refresh });
    useAuthStore.getState().setTokens(r.data.access_token, r.data.refresh_token);
    return r.data.access_token as string;
  } catch {
    return null;
  }
}
