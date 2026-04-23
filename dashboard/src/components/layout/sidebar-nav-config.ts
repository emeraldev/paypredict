import {
  BarChart3Icon,
  CheckCircle2Icon,
  FlaskConicalIcon,
  LayoutDashboardIcon,
  SettingsIcon,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", icon: LayoutDashboardIcon, label: "Dashboard" },
  { href: "/dashboard/analytics", icon: BarChart3Icon, label: "Analytics" },
  { href: "/dashboard/outcomes", icon: CheckCircle2Icon, label: "Outcomes" },
  { href: "/dashboard/backtest", icon: FlaskConicalIcon, label: "Backtest" },
  { href: "/dashboard/settings", icon: SettingsIcon, label: "Settings" },
];
