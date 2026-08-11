"use client";

import type { ScoresSummary } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCompactCurrency } from "@/lib/utils/format-currency";
import type { RiskLevel } from "@/lib/utils/format-risk";

interface SummaryCardsProps {
  summary: ScoresSummary;
  activeFilter: RiskLevel | null;
  onFilterChange: (filter: RiskLevel | null) => void;
}

interface RiskCardProps {
  label: string;
  value: number | string;
  subtitle: string;
  valueClass?: string;
  active?: boolean;
  onClick?: () => void;
}

function RiskCard({ label, value, subtitle, valueClass, active, onClick }: RiskCardProps) {
  const interactive = Boolean(onClick);
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      className={cn(
        "rounded-md border bg-card p-5 text-left transition-all",
        active
          ? "border-primary ring-1 ring-primary/40"
          : "border-border hover:border-primary/40",
        interactive ? "cursor-pointer" : "cursor-default",
      )}
    >
      <div className="mb-3 text-sm font-medium text-muted-foreground">{label}</div>
      <p
        className={cn(
          "text-4xl font-semibold tabular-nums tracking-tight text-foreground",
          valueClass,
        )}
      >
        {value}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
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
        subtitle="collections"
      />
      <RiskCard
        label="High risk"
        value={summary.high_risk}
        valueClass="text-risk-high-fg"
        subtitle={
          summary.total_value_at_risk > 0
            ? `${formatCompactCurrency(summary.total_value_at_risk, "ZAR")} at risk`
            : "no high-risk items"
        }
        active={activeFilter === "HIGH"}
        onClick={() => toggleFilter("HIGH")}
      />
      <RiskCard
        label="Medium risk"
        value={summary.medium_risk}
        valueClass="text-risk-med-fg"
        subtitle="need monitoring"
        active={activeFilter === "MEDIUM"}
        onClick={() => toggleFilter("MEDIUM")}
      />
      <RiskCard
        label="Low risk"
        value={summary.low_risk}
        valueClass="text-risk-low-fg"
        subtitle="on track"
        active={activeFilter === "LOW"}
        onClick={() => toggleFilter("LOW")}
      />
    </div>
  );
}
