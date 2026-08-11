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
  high_risk_batch: { icon: AlertTriangleIcon, colorClass: "text-risk-high" },
  collection_rate_drop: { icon: AlertCircleIcon, colorClass: "text-risk-med" },
  prediction_drift: { icon: AlertCircleIcon, colorClass: "text-risk-med" },
  outcome_spike: { icon: AlertTriangleIcon, colorClass: "text-risk-high" },
  card_health_warning: { icon: CreditCardIcon, colorClass: "text-risk-med" },
  backtest_complete: { icon: FlaskConicalIcon, colorClass: "text-risk-low" },
  bulk_scoring_complete: { icon: ZapIcon, colorClass: "text-primary" },
  api_key_unused: { icon: KeyIcon, colorClass: "text-muted-foreground" },
  // Activity
  weights_updated: { icon: SettingsIcon, colorClass: "text-muted-foreground" },
  team_member_invited: { icon: UserPlusIcon, colorClass: "text-muted-foreground" },
  team_member_joined: { icon: UserPlusIcon, colorClass: "text-risk-low" },
  api_key_created: { icon: KeyIcon, colorClass: "text-muted-foreground" },
  api_key_revoked: { icon: KeyIcon, colorClass: "text-risk-med" },
  alert_threshold_changed: { icon: SettingsIcon, colorClass: "text-muted-foreground" },
};

export function getNotificationIcon(eventType: string): NotificationIconConfig {
  return NOTIFICATION_ICONS[eventType] ?? { icon: BellIcon, colorClass: "text-muted-foreground" };
}

export function NotificationIcon({ eventType }: { eventType: string }) {
  const { icon: Icon, colorClass } = getNotificationIcon(eventType);
  return <Icon className={`h-4 w-4 shrink-0 ${colorClass}`} />;
}
