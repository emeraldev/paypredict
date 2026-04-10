import { format, formatDistanceToNow, isToday, isTomorrow, isPast } from "date-fns";

export function formatDate(date: string | Date): string {
  return format(new Date(date), "dd MMM yyyy");
}

export function formatRelativeDate(date: string | Date): {
  text: string;
  urgent: boolean;
} {
  const d = new Date(date);
  if (isPast(d) && !isToday(d)) return { text: "Overdue", urgent: true };
  if (isToday(d)) return { text: "Today", urgent: true };
  if (isTomorrow(d)) return { text: "Tomorrow", urgent: true };
  return { text: formatDistanceToNow(d, { addSuffix: true }), urgent: false };
}

export function formatDateTime(date: string | Date): string {
  return format(new Date(date), "dd MMM yyyy, HH:mm");
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}
