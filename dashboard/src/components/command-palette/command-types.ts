import type { LucideIcon } from "lucide-react";

export interface CommandItem {
  id: string;
  label: string;
  icon: LucideIcon;
  group: "Navigation" | "Quick Actions" | "Collections" | "Outcomes" | "Backtests";
  href: string;
  /** Optional secondary line shown in muted text under the label. */
  hint?: string;
  /** Optional keyboard shortcut hint shown on the right (e.g. "⌘K"). */
  shortcut?: string;
}
