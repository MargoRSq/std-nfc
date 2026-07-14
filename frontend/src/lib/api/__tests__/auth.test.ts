import { describe, it, expect, vi, beforeEach } from "vitest";
import type { TotpEnrollResponse, LoginRequest, TokenPair, LoginChallenge } from "../auth";

vi.mock("../client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import { apiClient } from "../client";
import { authApi } from "../auth";

const mockPost = vi.mocked(apiClient.post);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("authApi.login", () => {
  it("posts correct shape to /auth/login", async () => {
    const payload: LoginRequest = { email: "test@example.com", password: "pass123" };
    const response: TokenPair = {
      stage: "completed",
      access_token: "at",
      refresh_token: "rt",
      user: { id: "1", email: "test@example.com", role: "admin", is_active: true, totp_enabled: false, last_login_at: null, created_at: "2024-01-01T00:00:00Z" },
    };
    mockPost.mockResolvedValueOnce({ data: response });

    await authApi.login(payload);

    expect(mockPost).toHaveBeenCalledWith("/auth/login", payload);
  });

  it("returns challenge when totp is required", async () => {
    const challenge: LoginChallenge = { stage: "totp_required", challenge_token: "ctoken" };
    mockPost.mockResolvedValueOnce({ data: challenge });

    const result = await authApi.login({ email: "a@b.com", password: "x" });

    expect((result as { data: LoginChallenge }).data.stage).toBe("totp_required");
    expect((result as { data: LoginChallenge }).data.challenge_token).toBe("ctoken");
  });
});

describe("authApi.totpEnroll", () => {
  it("response has otpauth_url and qr_png_base64", async () => {
    const enrollResponse: TotpEnrollResponse = {
      otpauth_url: "otpauth://totp/STD%20RF:test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=STD%20RF",
      qr_png_base64: "iVBORw0KGgoAAAANSUhEUgAA...",
    };
    mockPost.mockResolvedValueOnce({ data: enrollResponse });

    const result = await authApi.totpEnroll();
    const data = (result as { data: TotpEnrollResponse }).data;

    expect(data).toHaveProperty("otpauth_url");
    expect(data).toHaveProperty("qr_png_base64");
    expect(data.otpauth_url).toContain("otpauth://totp/");
  });
});

describe("authApi.logout", () => {
  it("posts refresh_token to /auth/logout", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });

    await authApi.logout("my-refresh-token");

    expect(mockPost).toHaveBeenCalledWith("/auth/logout", { refresh_token: "my-refresh-token" });
  });
});
