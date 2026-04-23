import { StatCard } from "@/components/shared/stat-card";
import type { AnalyticsSummary } from "@/lib/api/types";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

interface AnalyticsStatCardsProps {
  summary: AnalyticsSummary;
}

export function AnalyticsStatCards({ summary }: AnalyticsStatCardsProps) {
  const rateChangePct = Math.round(summary.collection_rate_change * 100);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Scored"
        value={summary.total_scored.toLocaleString()}
        subtitle={`${summary.total_outcomes.toLocaleString()} outcomes reported`}
      />
      <StatCard
        title="Collection Rate"
        value={`${Math.round(summary.collection_rate * 100)}%`}
        trend={{ value: rateChangePct, label: "vs previous period" }}
      />
      <StatCard
        title="Value at Risk"
        value={formatCompactCurrency(summary.total_value_at_risk, "ZAR")}
        subtitle="High-risk collection sum"
      />
      <StatCard
        title="Prediction Accuracy"
        value={`${Math.round(summary.prediction_accuracy.overall_accuracy * 100)}%`}
        subtitle={`${Math.round(summary.outcomes_reporting_rate * 100)}% outcomes reported`}
        accentColor="border-l-emerald-500"
      />
    </div>
  );
}
