import { api } from "./client";

export interface AlertItem {
  id: string;
  alert_type: string;
  message: string;
  is_read: boolean;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

export interface AlertsResponse {
  items: AlertItem[];
  unread_count: number;
}

export const alertsApi = {
  list: (unreadOnly = false, limit = 20) =>
    api.get<AlertsResponse>(
      `/v1/alerts?unread_only=${unreadOnly}&limit=${limit}`,
    ),

  markRead: (id: string) => api.patch<unknown>(`/v1/alerts/${id}/read`, {}),

  markAllRead: () => api.patch<unknown>("/v1/alerts/read-all", {}),
};
