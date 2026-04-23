import { api, setToken, clearToken } from "./client";
import type { LoginRequest, LoginResponse, UserResponse } from "./types";

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
};
