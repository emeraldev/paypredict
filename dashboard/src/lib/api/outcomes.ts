import { api } from "./client";
import type { OutcomesListParams, OutcomesListResponse } from "./types";

export interface ReportOutcomePayload {
  score_id?: string;
  collection_id: string;
  outcome: "SUCCESS" | "FAILED";
  failure_reason?: string;
  amount_collected?: number;
  attempted_at: string;
}

export interface OutcomeCreatedResponse {
  outcome_id: string;
  linked_score_id: string | null;
  received_at: string;
}

function buildQuery(params: OutcomesListParams): string {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size));
  if (params.outcome) search.set("outcome", params.outcome);
  if (params.match) search.set("match", params.match);
  if (params.search) search.set("search", params.search);
  if (params.date_from) search.set("date_from", params.date_from);
  if (params.date_to) search.set("date_to", params.date_to);
  if (params.sort_by) search.set("sort_by", params.sort_by);
  if (params.sort_order) search.set("sort_order", params.sort_order);
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const outcomesApi = {
  list: (params: OutcomesListParams = {}) =>
    api.get<OutcomesListResponse>(`/v1/outcomes${buildQuery(params)}`),

  create: (payload: ReportOutcomePayload) =>
    api.post<OutcomeCreatedResponse>("/v1/outcomes", payload),
};
