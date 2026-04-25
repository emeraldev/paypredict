"use client";

import { BellIcon } from "lucide-react";
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
          <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
            <BellIcon className="h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm">No notifications yet</p>
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
