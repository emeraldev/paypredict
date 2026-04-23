import { api } from "./client";
import type {
  AlertSettings,
  ApiKeyCreateResponse,
  ApiKeyListItem,
  ApiKeyListResponse,
  TeamListResponse,
  TeamMember,
  WeightsResponse,
} from "./types";

export const configApi = {
  // Weights
  getWeights: () => api.get<WeightsResponse>("/v1/config/weights"),
  updateWeights: (weights: Record<string, number>) =>
    api.put<WeightsResponse>("/v1/config/weights", { weights }),

  // API Keys
  getApiKeys: () => api.get<ApiKeyListResponse>("/v1/config/api-keys"),
  createApiKey: (label: string) =>
    api.post<ApiKeyCreateResponse>("/v1/config/api-keys", { label }),
  toggleApiKey: (id: string, is_active: boolean) =>
    api.patch<ApiKeyListItem>(`/v1/config/api-keys/${id}`, { is_active }),
  revokeApiKey: (id: string) => api.delete<void>(`/v1/config/api-keys/${id}`),

  // Team
  getTeam: () => api.get<TeamListResponse>("/v1/config/team"),
  inviteMember: (data: { email: string; name: string; password: string; role: string }) =>
    api.post<TeamMember>("/v1/config/team", data),
  updateMemberRole: (id: string, role: string) =>
    api.patch<TeamMember>(`/v1/config/team/${id}`, { role }),
  removeMember: (id: string) => api.delete<void>(`/v1/config/team/${id}`),

  // Alerts
  getAlertSettings: () => api.get<AlertSettings>("/v1/config/alerts"),
  updateAlertSettings: (settings: Partial<AlertSettings>) =>
    api.put<AlertSettings>("/v1/config/alerts", settings),
};
