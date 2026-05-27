import { api } from "./client";
import type {
  CollectionsListParams,
  CollectionsListResponse,
  ScoreDetailResponse,
  ScoreRequestPayload,
  ScoreResponse,
} from "./types";

function buildQuery(params: CollectionsListParams): string {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size));
  if (params.risk_level) search.set("risk_level", params.risk_level);
  if (params.collection_method) search.set("collection_method", params.collection_method);
  if (params.recommended_action) search.set("recommended_action", params.recommended_action);
  if (params.search) search.set("search", params.search);
  if (params.date_from) search.set("due_date_from", params.date_from);
  if (params.date_to) search.set("due_date_to", params.date_to);
  if (params.sort_by) search.set("sort_by", params.sort_by);
  if (params.sort_order) search.set("sort_order", params.sort_order);
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export interface ScoredUploadRow {
  score_id: string;
  customer_id: string;
  collection_id: string;
  collection_amount: number;
  collection_currency: string;
  collection_due_date: string;
  collection_method: string;
  score: number;
  risk_level: string;
  recommended_action: string;
  recommended_collection_date: string | null;
  recommended_score: number | null;
  score_improvement: number | null;
  model_version: string;
}

export interface ScoresUploadResponse {
  // Validation-error response shape
  errors?: { row: number; field: string; message: string }[];
  // Successful upload response shape (mirrors bulk-scoring response)
  status?: string;
  total_items?: number;
  completed_items?: number;
  summary?: {
    high_risk: number;
    medium_risk: number;
    low_risk: number;
    total_value_at_risk: number;
  };
  results?: ScoredUploadRow[];
}

export const scoresApi = {
  list: (params: CollectionsListParams = {}) =>
    api.get<CollectionsListResponse>(`/v1/scores${buildQuery(params)}`),

  getDetail: (scoreId: string) =>
    api.get<ScoreDetailResponse>(`/v1/scores/${scoreId}`),

  create: (payload: ScoreRequestPayload) =>
    api.post<ScoreResponse>("/v1/score", payload),

  /**
   * Upload a CSV of upcoming collections. Multipart form-data, so this
   * bypasses the shared `api` client (which assumes JSON). Same FormData
   * pattern as backtestApi.uploadCsv.
   */
  uploadCsv: async (file: File): Promise<ScoresUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    const token = typeof window !== "undefined"
      ? localStorage.getItem("paypredict_token")
      : null;

    const res = await fetch(`${API_URL}/v1/scores/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      if (body.errors) return body;
      throw new Error(body.detail || "Upload failed");
    }

    return res.json();
  },

  templateUrl: () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    return `${API_URL}/v1/scores/upload/template`;
  },
};
