import {
  AlertCircleIcon,
  AlertTriangleIcon,
  BellIcon,
  CreditCardIcon,
  FlaskConicalIcon,
  InfoIcon,
  KeyIcon,
  SettingsIcon,
  UserPlusIcon,
  ZapIcon,
  type LucideIcon,
} from "lucide-react";

interface NotificationIconConfig {
  icon: LucideIcon;
  colorClass: string;
}

// SINGLE SOURCE OF TRUTH for notification icons
const NOTIFICATION_ICONS: Record<string, NotificationIconConfig> = {
  // System
  high_risk_batch: { icon: AlertTriangleIcon, colorClass: "text-red-500" },
  collection_rate_drop: { icon: AlertCircleIcon, colorClass: "text-amber-500" },
  prediction_drift: { icon: AlertCircleIcon, colorClass: "text-amber-500" },
  outcome_spike: { icon: AlertTriangleIcon, colorClass: "text-red-500" },
  card_health_warning: { icon: CreditCardIcon, colorClass: "text-amber-500" },
  backtest_complete: { icon: FlaskConicalIcon, colorClass: "text-emerald-500" },
  bulk_scoring_complete: { icon: ZapIcon, colorClass: "text-blue-500" },
  api_key_unused: { icon: KeyIcon, colorClass: "text-zinc-400" },
  // Activity
  weights_updated: { icon: SettingsIcon, colorClass: "text-zinc-400" },
  team_member_invited: { icon: UserPlusIcon, colorClass: "text-zinc-400" },
  team_member_joined: { icon: UserPlusIcon, colorClass: "text-emerald-500" },
  api_key_created: { icon: KeyIcon, colorClass: "text-zinc-400" },
  api_key_revoked: { icon: KeyIcon, colorClass: "text-amber-500" },
  alert_threshold_changed: { icon: SettingsIcon, colorClass: "text-zinc-400" },
};

export function getNotificationIcon(eventType: string): NotificationIconConfig {
  return NOTIFICATION_ICONS[eventType] ?? { icon: BellIcon, colorClass: "text-zinc-400" };
}

export function NotificationIcon({ eventType }: { eventType: string }) {
  const { icon: Icon, colorClass } = getNotificationIcon(eventType);
  return <Icon className={`h-4 w-4 shrink-0 ${colorClass}`} />;
}
