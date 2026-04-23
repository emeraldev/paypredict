import { api } from "./client";
import type {
  AnalyticsSummary,
  CollectionRatePoint,
  FactorContribution,
} from "./types";

export type AnalyticsPeriod = "7d" | "30d" | "90d" | "12m";

export const analyticsApi = {
  summary: (period: AnalyticsPeriod = "30d") =>
    api.get<AnalyticsSummary>(`/v1/analytics/summary?period=${period}`),

  collectionRate: (period: AnalyticsPeriod = "30d") =>
    api.get<CollectionRatePoint[]>(`/v1/analytics/collection-rate?period=${period}`),

  factorContributions: (period: AnalyticsPeriod = "30d") =>
    api.get<FactorContribution[]>(`/v1/analytics/factors?period=${period}`),
};
