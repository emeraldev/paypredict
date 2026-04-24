import { api } from "./client";
import type {
  BacktestListResponse,
  BacktestResponse,
  BacktestRequest,
} from "./types";

export const backtestApi = {
  run: (data: BacktestRequest) =>
    api.post<BacktestResponse>("/v1/backtest", data),

  uploadCsv: async (file: File): Promise<BacktestResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    const token = typeof window !== "undefined" ? localStorage.getItem("paypredict_token") : null;

    const res = await fetch(`${API_URL}/v1/backtest/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      // If validation errors, return them as-is
      if (body.errors) return body;
      throw new Error(body.detail || "Upload failed");
    }

    return res.json();
  },

  get: (id: string) =>
    api.get<BacktestResponse>(`/v1/backtest/${id}`),

  list: () =>
    api.get<BacktestListResponse>("/v1/backtests"),

  templateUrl: () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    return `${API_URL}/v1/backtest/template`;
  },
};
