import { api } from "./client";

export interface NotificationItem {
  id: string;
  category: "SYSTEM" | "ACTIVITY";
  severity: "CRITICAL" | "WARNING" | "INFO";
  event_type: string;
  title: string;
  message: string;
  link_to: string | null;
  link_label: string | null;
  metadata: Record<string, unknown> | null;
  actor: { id: string; name: string } | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
  unread_count: number;
}

export const notificationsApi = {
  list: (params?: { page?: number; page_size?: number; unread_only?: boolean }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.unread_only) query.set("unread_only", "true");
    const qs = query.toString();
    return api.get<NotificationsResponse>(`/v1/notifications${qs ? `?${qs}` : ""}`);
  },

  unreadCount: () =>
    api.get<{ unread_count: number }>("/v1/notifications/unread-count"),

  markRead: (id: string) =>
    api.patch<unknown>(`/v1/notifications/${id}/read`, {}),

  markAllRead: () =>
    api.post<unknown>("/v1/notifications/read-all", {}),
};
