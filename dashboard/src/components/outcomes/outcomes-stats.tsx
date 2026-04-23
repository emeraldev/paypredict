import { StatCard } from "@/components/shared/stat-card";
import type { OutcomeListStats } from "@/lib/api/types";

interface OutcomesStatsProps {
  stats: OutcomeListStats;
}

export function OutcomesStats({ stats }: OutcomesStatsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Reported"
        value={stats.total_outcomes.toLocaleString()}
        subtitle="Outcomes received"
      />
      <StatCard
        title="Collection Rate"
        value={`${Math.round(stats.success_rate * 100)}%`}
        subtitle={`${stats.success_count} succeeded, ${stats.failed_count} failed`}
      />
      <StatCard
        title="Match Rate"
        value={`${Math.round(stats.match_rate * 100)}%`}
        subtitle={`${stats.predictions_matched} matched`}
      />
      <StatCard
        title="Failed"
        value={stats.failed_count.toLocaleString()}
        subtitle="Collections that failed"
      />
    </div>
  );
}
