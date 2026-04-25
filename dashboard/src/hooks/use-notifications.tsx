"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { notificationsApi, type NotificationItem } from "@/lib/api/notifications";
import { getToken } from "@/lib/api/client";

const POLL_INTERVAL = 30_000; // 30 seconds

export function useNotifications() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await notificationsApi.list({ page_size: 10 });
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch {
      // Silently fail — bell just shows stale count
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll unread count every 30 seconds
  useEffect(() => {
    // Don't poll if not authenticated
    if (!getToken()) return;

    fetchNotifications();

    const interval = setInterval(async () => {
      try {
        const { unread_count } = await notificationsApi.unreadCount();
        setUnreadCount(unread_count);
      } catch {
        // Silently fail
      }
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const markAsRead = useCallback(async (id: string) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Silently fail
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  }, []);

  return {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  };
}
