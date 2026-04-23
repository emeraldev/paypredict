"use client";

import { AnalyticsStatCards } from "@/components/analytics/analytics-stat-cards";
import { CollectionRateChart } from "@/components/analytics/collection-rate-chart";
import { FailureFactorsChart } from "@/components/analytics/failure-factors-chart";
import { PredictionAccuracyChart } from "@/components/analytics/prediction-accuracy-chart";
import { RiskDistributionChart } from "@/components/analytics/risk-distribution-chart";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { analyticsApi } from "@/lib/api/analytics";

export default function AnalyticsPage() {
  const { data: summary, loading: loadingSummary, error: summaryError } = useApi(
    () => analyticsApi.summary("30d"),
    [],
  );
  const { data: rateData, loading: loadingRate } = useApi(
    () => analyticsApi.collectionRate("30d"),
    [],
  );
  const { data: factorsData, loading: loadingFactors } = useApi(
    () => analyticsApi.factors("30d"),
    [],
  );

  if (summaryError) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
        Failed to load analytics: {summaryError}
      </div>
    );
  }

  const loading = loadingSummary || loadingRate || loadingFactors;

  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton variant="cards" count={4} />
        <LoadingSkeleton variant="chart" count={4} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CollectionRateChart data={rateData?.data_points ?? []} />
        {summary && <RiskDistributionChart data={summary.risk_distribution} />}
        {summary && <PredictionAccuracyChart data={summary.prediction_accuracy} />}
        <FailureFactorsChart data={factorsData?.factors ?? []} />
      </div>

      {summary && <AnalyticsStatCards summary={summary} />}
    </div>
  );
}
