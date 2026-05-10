import {
  BarChart3Icon,
  BellIcon,
  CheckCircle2Icon,
  FileCodeIcon,
  FlaskConicalIcon,
  KeyIcon,
  LayoutDashboardIcon,
  SettingsIcon,
  UsersIcon,
} from "lucide-react";

import type { CommandItem } from "./command-types";

/** Always-visible commands when the search input is empty. */
export const STATIC_COMMANDS: CommandItem[] = [
  // Navigation
  {
    id: "nav-dashboard",
    label: "Go to Dashboard",
    icon: LayoutDashboardIcon,
    group: "Navigation",
    href: "/dashboard",
  },
  {
    id: "nav-analytics",
    label: "Go to Analytics",
    icon: BarChart3Icon,
    group: "Navigation",
    href: "/dashboard/analytics",
  },
  {
    id: "nav-outcomes",
    label: "Go to Outcomes",
    icon: CheckCircle2Icon,
    group: "Navigation",
    href: "/dashboard/outcomes",
  },
  {
    id: "nav-backtest",
    label: "Go to Backtest",
    icon: FlaskConicalIcon,
    group: "Navigation",
    href: "/dashboard/backtest",
  },
  {
    id: "nav-settings",
    label: "Go to Settings",
    icon: SettingsIcon,
    group: "Navigation",
    href: "/dashboard/settings",
  },

  // Quick Actions
  {
    id: "qa-api-keys",
    label: "Manage API Keys",
    icon: KeyIcon,
    group: "Quick Actions",
    href: "/dashboard/settings",
  },
  {
    id: "qa-team",
    label: "Manage Team",
    icon: UsersIcon,
    group: "Quick Actions",
    href: "/dashboard/settings",
  },
  {
    id: "qa-alerts",
    label: "Configure Alerts",
    icon: BellIcon,
    group: "Quick Actions",
    href: "/dashboard/settings",
  },
  {
    id: "qa-api-docs",
    label: "View API Docs",
    icon: FileCodeIcon,
    group: "Quick Actions",
    href: "/docs",
  },
];
