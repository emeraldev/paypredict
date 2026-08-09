import type { CollectionMethod } from "@/lib/utils/format-method";
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
  // Weights — grouped per collection_method. Updates target ONE method at
  // a time; other methods' weights are untouched.
  getWeights: () => api.get<WeightsResponse>("/v1/config/weights"),
  updateWeights: (
    collection_method: CollectionMethod,
    weights: Record<string, number>,
  ) =>
    api.put<WeightsResponse>("/v1/config/weights", {
      collection_method,
      weights,
    }),
  // Opt in to a new method — seeds default weights so a tab appears
  // before the tenant scores their first collection with that method.
  // Idempotent for methods that already have weights.
  addWeightsMethod: (collection_method: CollectionMethod) =>
    api.post<WeightsResponse>("/v1/config/weights/methods", {
      collection_method,
    }),

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
  rotateWebhookSecret: () =>
    api.post<AlertSettings>("/v1/config/alerts/regenerate-secret", {}),
};
