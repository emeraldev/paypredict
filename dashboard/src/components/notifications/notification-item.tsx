"use client";

import { useRouter } from "next/navigation";
import type { NotificationItem as NotificationType } from "@/lib/api/notifications";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/utils/format-date";
import { NotificationIcon } from "./notification-icon";

interface NotificationItemProps {
  notification: NotificationType;
  onRead: (id: string) => void;
  onClose: () => void;
}

export function NotificationItem({ notification, onRead, onClose }: NotificationItemProps) {
  const router = useRouter();

  const handleClick = () => {
    if (!notification.is_read) {
      onRead(notification.id);
    }
    if (notification.link_to) {
      onClose();
      router.push(notification.link_to);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "flex w-full items-start gap-3 border-l-2 px-4 py-3 text-left transition-colors hover:bg-accent/40",
        notification.is_read
          ? "border-l-transparent"
          : "border-l-blue-500 bg-accent/20",
      )}
    >
      <div className="mt-0.5">
        <NotificationIcon eventType={notification.event_type} />
      </div>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-[13px] font-medium",
            notification.is_read ? "text-muted-foreground" : "text-foreground",
          )}
        >
          {notification.title}
        </p>
        <p
          className={cn(
            "mt-0.5 line-clamp-2 text-xs",
            notification.is_read ? "text-muted-foreground/70" : "text-muted-foreground",
          )}
        >
          {notification.message}
        </p>
        {notification.link_to && notification.link_label && (
          <p className="mt-1 text-xs text-blue-500">{notification.link_label} &rarr;</p>
        )}
      </div>
      <span className="shrink-0 text-[11px] text-muted-foreground/60">
        {formatRelativeTime(notification.created_at)}
      </span>
    </button>
  );
}
