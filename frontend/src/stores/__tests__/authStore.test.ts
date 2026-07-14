import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "../authStore";

beforeEach(() => {
  useAuthStore.setState({
    accessToken: null,
    refreshToken: null,
    user: null,
  });
});

describe("useAuthStore", () => {
  it("setTokens persists access and refresh tokens", () => {
    useAuthStore.getState().setTokens("access-abc", "refresh-xyz");

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-abc");
    expect(state.refreshToken).toBe("refresh-xyz");
  });

  it("logout clears all auth state", () => {
    useAuthStore.getState().setTokens("at", "rt");
    useAuthStore.getState().setUser({ id: "1", email: "a@b.com", role: "admin" });

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it("access_token getter returns current access token", () => {
    expect(useAuthStore.getState().accessToken).toBeNull();
    useAuthStore.getState().setTokens("my-token", "my-refresh");
    expect(useAuthStore.getState().accessToken).toBe("my-token");
  });

  it("setUser updates user without affecting tokens", () => {
    useAuthStore.getState().setTokens("at", "rt");
    useAuthStore.getState().setUser({ id: "u1", email: "user@test.com", role: "viewer" });

    const state = useAuthStore.getState();
    expect(state.user?.email).toBe("user@test.com");
    expect(state.accessToken).toBe("at");
  });
});
