import { StatCard } from "@/components/shared/stat-card";
import type { OutcomeStats } from "@/lib/api/types";

interface OutcomesStatsProps {
  stats: OutcomeStats;
}

export function OutcomesStats({ stats }: OutcomesStatsProps) {
  const accuracy =
    stats.matched + stats.mismatched > 0
      ? Math.round((stats.matched / (stats.matched + stats.mismatched)) * 100)
      : 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Reported"
        value={stats.total_reported.toLocaleString()}
        subtitle="Outcomes received"
      />
      <StatCard
        title="Collection Rate"
        value={`${Math.round(stats.collection_rate * 100)}%`}
        subtitle="Successful / total"
      />
      <StatCard
        title="Prediction Accuracy"
        value={`${accuracy}%`}
        subtitle={`${stats.matched} matched, ${stats.mismatched} mismatched`}
      />
      <StatCard
        title="Pending"
        value={stats.pending.toLocaleString()}
        subtitle="Awaiting result"
      />
    </div>
  );
}
