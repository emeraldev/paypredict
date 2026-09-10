import { api, setToken, clearToken } from "./client";
import type {
  ChangePasswordRequest,
  ChangePasswordResponse,
  LoginRequest,
  LoginResponse,
  UserResponse,
} from "./types";

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>("/v1/auth/login", credentials, {
      skipAuth: true,
    });
    setToken(res.token);
    return res;
  },

  me: () => api.get<UserResponse>("/v1/auth/me"),

  logout: async (): Promise<void> => {
    try {
      await api.post<unknown>("/v1/auth/logout", {});
    } finally {
      clearToken();
    }
  },

  // Server rotates the password AND invalidates every prior JWT (via
  // password_changed_at). The response includes a fresh token so we
  // swap it in-place — the old one is already dead server-side.
  changePassword: async (
    payload: ChangePasswordRequest,
  ): Promise<ChangePasswordResponse> => {
    const res = await api.post<ChangePasswordResponse>(
      "/v1/auth/change-password",
      payload,
    );
    setToken(res.token);
    return res;
  },
};
