import {
  BarChart3Icon,
  CheckCircle2Icon,
  FileCodeIcon,
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
  /** External links open in a new tab and get an arrow affordance. */
  external?: boolean;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

const API_DOCS_HREF = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"}/docs`;

export const SIDEBAR_SECTIONS: NavSection[] = [
  {
    title: "COLLECTIONS",
    items: [
      { href: "/dashboard", icon: LayoutDashboardIcon, label: "Dashboard" },
      {
        href: "/dashboard/score",
        icon: UploadIcon,
        label: "Score Collections",
        description: "Upload a CSV of upcoming collections to score them by risk",
      },
      {
        href: "/dashboard/outcomes",
        icon: CheckCircle2Icon,
        label: "Outcomes",
        description: "Reported collection results. Predicted risk vs. what actually happened.",
      },
    ],
  },
  {
    title: "ANALYSIS",
    items: [
      { href: "/dashboard/analytics", icon: BarChart3Icon, label: "Analytics" },
      {
        href: "/dashboard/backtest",
        icon: FlaskConicalIcon,
        label: "Backtest",
        description: "Re-score past collections against the current model to test accuracy",
      },
    ],
  },
  {
    title: "SETTINGS",
    items: [
      { href: "/dashboard/settings", icon: SettingsIcon, label: "Settings" },
      {
        href: API_DOCS_HREF,
        icon: FileCodeIcon,
        label: "API Documentation",
        external: true,
      },
    ],
  },
];

// Flat list kept for anywhere that still enumerates every route (e.g. the
// command palette). Prefer SIDEBAR_SECTIONS when rendering the sidebar.
export const NAV_ITEMS: NavItem[] = SIDEBAR_SECTIONS.flatMap((s) => s.items);
