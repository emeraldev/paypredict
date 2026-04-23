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
  if (params.search) search.set("search", params.search);
  if (params.date_from) search.set("due_date_from", params.date_from);
  if (params.date_to) search.set("due_date_to", params.date_to);
  if (params.sort_by) search.set("sort_by", params.sort_by);
  if (params.sort_order) search.set("sort_order", params.sort_order);
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const scoresApi = {
  list: (params: CollectionsListParams = {}) =>
    api.get<CollectionsListResponse>(`/v1/scores${buildQuery(params)}`),

  getDetail: (scoreId: string) =>
    api.get<ScoreDetailResponse>(`/v1/scores/${scoreId}`),

  create: (payload: ScoreRequestPayload) =>
    api.post<ScoreResponse>("/v1/score", payload),
};
