"use client";

import {
  AlertCircleIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  ClockIcon,
  type LucideIcon,
} from "lucide-react";
import type { ScoresSummary } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCompactCurrency } from "@/lib/utils/format-currency";
import type { RiskLevel } from "@/lib/utils/format-risk";

interface SummaryCardsProps {
  summary: ScoresSummary;
  activeFilter: RiskLevel | null;
  onFilterChange: (filter: RiskLevel | null) => void;
}

interface RiskTone {
  text: string;
  subtle: string;
  bg: string;
  border: string;
  hoverBorder: string;
  ring: string;
}

const NEUTRAL_TONE: RiskTone = {
  text: "text-foreground",
  subtle: "text-muted-foreground",
  bg: "bg-card",
  border: "border-border",
  hoverBorder: "hover:border-border/80",
  ring: "ring-foreground/30",
};

const HIGH_TONE: RiskTone = {
  text: "text-red-700 dark:text-red-400",
  subtle: "text-red-700/60 dark:text-red-400/60",
  bg: "bg-red-50 dark:bg-red-950/50",
  border: "border-red-500/40 dark:border-red-500/30",
  hoverBorder: "hover:border-red-500/70 dark:hover:border-red-500/60",
  ring: "ring-red-500",
};

const MEDIUM_TONE: RiskTone = {
  text: "text-amber-700 dark:text-amber-400",
  subtle: "text-amber-700/60 dark:text-amber-400/60",
  bg: "bg-amber-50 dark:bg-amber-950/50",
  border: "border-amber-500/40 dark:border-amber-500/30",
  hoverBorder: "hover:border-amber-500/70 dark:hover:border-amber-500/60",
  ring: "ring-amber-500",
};

const LOW_TONE: RiskTone = {
  text: "text-emerald-700 dark:text-emerald-400",
  subtle: "text-emerald-700/60 dark:text-emerald-400/60",
  bg: "bg-emerald-50 dark:bg-emerald-950/50",
  border: "border-emerald-500/40 dark:border-emerald-500/30",
  hoverBorder: "hover:border-emerald-500/70 dark:hover:border-emerald-500/60",
  ring: "ring-emerald-500",
};

interface RiskCardProps {
  label: string;
  value: number | string;
  subtitle: string;
  icon: LucideIcon;
  tone: RiskTone;
  active?: boolean;
  onClick?: () => void;
}

function RiskCard({ label, value, subtitle, icon: Icon, tone, active, onClick }: RiskCardProps) {
  const interactive = Boolean(onClick);
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      className={cn(
        "rounded-xl border p-5 text-left transition-all",
        tone.bg,
        tone.border,
        interactive && [tone.hoverBorder, "cursor-pointer"],
        active && ["ring-1", tone.ring, "border-transparent"],
        !interactive && "cursor-default",
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className={cn("text-sm font-medium", tone.text)}>{label}</span>
        <Icon className={cn("h-4 w-4", tone.text)} />
      </div>
      <p className={cn("text-4xl font-bold tabular-nums tracking-tight", tone.text)}>
        {value}
      </p>
      <p className={cn("mt-1 text-sm", tone.subtle)}>{subtitle}</p>
    </button>
  );
}

export function SummaryCards({
  summary,
  activeFilter,
  onFilterChange,
}: SummaryCardsProps) {
  const total = summary.high_risk + summary.medium_risk + summary.low_risk;

  const toggleFilter = (level: RiskLevel) => {
    onFilterChange(activeFilter === level ? null : level);
  };

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <RiskCard
        label="Upcoming"
        value={total}
        subtitle="collections pending"
        icon={ClockIcon}
        tone={NEUTRAL_TONE}
      />
      <RiskCard
        label="High Risk"
        value={summary.high_risk}
        subtitle={
          summary.total_value_at_risk > 0
            ? `${formatCompactCurrency(summary.total_value_at_risk, "ZAR")} at risk`
            : "no high-risk items"
        }
        icon={AlertTriangleIcon}
        tone={HIGH_TONE}
        active={activeFilter === "HIGH"}
        onClick={() => toggleFilter("HIGH")}
      />
      <RiskCard
        label="Medium Risk"
        value={summary.medium_risk}
        subtitle="need monitoring"
        icon={AlertCircleIcon}
        tone={MEDIUM_TONE}
        active={activeFilter === "MEDIUM"}
        onClick={() => toggleFilter("MEDIUM")}
      />
      <RiskCard
        label="Low Risk"
        value={summary.low_risk}
        subtitle="looking good"
        icon={CheckCircle2Icon}
        tone={LOW_TONE}
        active={activeFilter === "LOW"}
        onClick={() => toggleFilter("LOW")}
      />
    </div>
  );
}
