import { api } from "./client";
import type { OutcomesListParams, OutcomesListResponse } from "./types";

function buildQuery(params: OutcomesListParams): string {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size));
  if (params.filter) search.set("filter", params.filter);
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const outcomesApi = {
  list: (params: OutcomesListParams = {}) =>
    api.get<OutcomesListResponse>(`/v1/outcomes${buildQuery(params)}`),
};
