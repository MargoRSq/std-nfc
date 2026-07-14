import { apiClient } from "./client";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginChallenge {
  stage: "totp_required";
  challenge_token: string;
}

export interface UserPublic {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  totp_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenPair {
  stage?: "completed";
  access_token: string;
  refresh_token: string;
  user: UserPublic;
}

export type LoginResponse = LoginChallenge | TokenPair;

export interface TotpLoginRequest {
  challenge_token: string;
  code: string;
}

export interface RecoveryLoginRequest {
  challenge_token: string;
  recovery_code: string;
}

export interface TotpEnrollResponse {
  otpauth_url: string;
  qr_png_base64: string;
}

export interface TotpVerifyResponse {
  recovery_codes: string[];
}

export const authApi = {
  login: (data: LoginRequest) => apiClient.post<LoginResponse>("/auth/login", data),
  loginTotp: (data: TotpLoginRequest) => apiClient.post<TokenPair>("/auth/login/totp", data),
  loginRecovery: (data: RecoveryLoginRequest) => apiClient.post<TokenPair>("/auth/login/recovery", data),
  logout: (refresh_token: string) => apiClient.post("/auth/logout", { refresh_token }),
  refresh: (refresh_token: string) =>
    apiClient.post<TokenPair>("/auth/refresh", { refresh_token }),
  me: () => apiClient.get<UserPublic>("/auth/me"),
  totpEnroll: () => apiClient.post<TotpEnrollResponse>("/auth/totp/enroll"),
  totpVerify: (code: string) =>
    apiClient.post<TotpVerifyResponse>("/auth/totp/verify", { code }),
  totpDisable: (password: string, code: string) =>
    apiClient.post("/auth/totp/disable", { password, code }),
  passwordResetRequest: (email: string) =>
    apiClient.post("/auth/password/reset/request", { email }),
  passwordResetConfirm: (token: string, new_password: string) =>
    apiClient.post("/auth/password/reset/confirm", { token, new_password }),
  changePassword: (old_password: string, new_password: string) =>
    apiClient.post("/auth/password/change", { old_password, new_password }),
};
