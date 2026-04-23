import { api } from "./client";
import type {
  AccuracyResponse,
  AnalyticsSummary,
  CollectionRateResponse,
  FactorsResponse,
} from "./types";

export type AnalyticsPeriod = "7d" | "14d" | "30d" | "60d" | "90d";

export const analyticsApi = {
  summary: (period: AnalyticsPeriod = "30d") =>
    api.get<AnalyticsSummary>(`/v1/analytics/summary?period=${period}`),

  collectionRate: (period: AnalyticsPeriod = "30d", interval: "daily" | "weekly" = "daily") =>
    api.get<CollectionRateResponse>(
      `/v1/analytics/collection-rate?period=${period}&interval=${interval}`,
    ),

  factors: (period: AnalyticsPeriod = "30d") =>
    api.get<FactorsResponse>(`/v1/analytics/factors?period=${period}`),

  accuracy: (period: AnalyticsPeriod = "30d") =>
    api.get<AccuracyResponse>(`/v1/analytics/accuracy?period=${period}`),
};
