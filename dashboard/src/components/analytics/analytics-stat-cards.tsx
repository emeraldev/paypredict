import { StatCard } from "@/components/shared/stat-card";
import type { AnalyticsSummary } from "@/lib/api/types";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

interface AnalyticsStatCardsProps {
  summary: AnalyticsSummary;
}

export function AnalyticsStatCards({ summary }: AnalyticsStatCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Scored"
        value={summary.total_scored.toLocaleString()}
        subtitle={`${summary.total_outcomes_reported.toLocaleString()} outcomes reported`}
      />
      <StatCard
        title="Collection Rate"
        value={`${Math.round(summary.collection_rate * 100)}%`}
        trend={{ value: 3.2, label: "vs last period" }}
      />
      <StatCard
        title="Value at Risk"
        value={formatCompactCurrency(summary.value_at_risk, "ZAR")}
        subtitle="High-risk collection sum"
      />
      <StatCard
        title="Recovered vs Baseline"
        value={`+${formatCompactCurrency(summary.value_recovered_vs_baseline, "ZAR")}`}
        subtitle="Estimated uplift"
        accentColor="border-l-emerald-500"
      />
    </div>
  );
}
