import { api } from "./client";
import type {
  AlertSettings,
  ApiKey,
  TeamMember,
  Tenant,
  WeightsResponse,
} from "./types";

export const configApi = {
  getTenant: () => api.get<Tenant>("/v1/config/tenant"),

  getWeights: () => api.get<WeightsResponse>("/v1/config/weights"),

  updateWeights: (weights: Record<string, number>) =>
    api.put<WeightsResponse>("/v1/config/weights", { weights }),

  getApiKeys: () => api.get<ApiKey[]>("/v1/config/api-keys"),

  createApiKey: (label: string) =>
    api.post<{ key: ApiKey; raw_key: string }>("/v1/config/api-keys", { label }),

  revokeApiKey: (id: string) => api.delete<void>(`/v1/config/api-keys/${id}`),

  getTeam: () => api.get<TeamMember[]>("/v1/config/team"),

  getAlertSettings: () => api.get<AlertSettings>("/v1/config/alerts"),

  updateAlertSettings: (settings: Partial<AlertSettings>) =>
    api.put<AlertSettings>("/v1/config/alerts", settings),
};
