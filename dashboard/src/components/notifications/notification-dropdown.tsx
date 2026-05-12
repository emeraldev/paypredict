"use client";

import { CheckCheckIcon } from "lucide-react";
import type { NotificationItem as NotificationType } from "@/lib/api/notifications";
import { NotificationItem } from "./notification-item";

interface NotificationDropdownProps {
  notifications: NotificationType[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onClose: () => void;
}

export function NotificationDropdown({
  notifications,
  onMarkRead,
  onMarkAllRead,
  onClose,
}: NotificationDropdownProps) {
  const hasUnread = notifications.some((n) => !n.is_read);

  return (
    <div className="w-[380px] max-h-[480px] overflow-hidden rounded-lg border border-border bg-popover shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
        {hasUnread && (
          <button
            type="button"
            onClick={onMarkAllRead}
            className="text-xs text-blue-500 hover:text-blue-400"
          >
            Mark all as read
          </button>
        )}
      </div>

      {/* List */}
      <div className="max-h-[400px] overflow-y-auto divide-y divide-border/50">
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/60 text-muted-foreground ring-1 ring-border/60">
              <CheckCheckIcon className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">You&apos;re all caught up</p>
              <p className="text-xs text-muted-foreground">
                Alerts, weight changes, and key activity will appear here.
              </p>
            </div>
          </div>
        ) : (
          notifications.map((n) => (
            <NotificationItem
              key={n.id}
              notification={n}
              onRead={onMarkRead}
              onClose={onClose}
            />
          ))
        )}
      </div>
    </div>
  );
}
