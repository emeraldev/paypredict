import {
  BarChart3Icon,
  CheckCircle2Icon,
  FlaskConicalIcon,
  LayoutDashboardIcon,
  SettingsIcon,
  UploadIcon,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
  /** Plain-English explanation shown as a hover tooltip when the
   *  sidebar is expanded. Helpful for jargon-y nav items like
   *  "Backtest" that a first-time admin won't recognise. */
  description?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", icon: LayoutDashboardIcon, label: "Dashboard" },
  {
    href: "/dashboard/score",
    icon: UploadIcon,
    label: "Score Collections",
    description: "Upload a CSV of upcoming collections to score them by risk",
  },
  { href: "/dashboard/analytics", icon: BarChart3Icon, label: "Analytics" },
  {
    href: "/dashboard/outcomes",
    icon: CheckCircle2Icon,
    label: "Outcomes",
    description: "Reported collection results — predicted risk vs. what actually happened",
  },
  {
    href: "/dashboard/backtest",
    icon: FlaskConicalIcon,
    label: "Backtest",
    description: "Re-score past collections against the current model to test accuracy",
  },
  { href: "/dashboard/settings", icon: SettingsIcon, label: "Settings" },
];
