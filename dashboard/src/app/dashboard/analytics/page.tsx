"use client";

import { useState } from "react";
import { AnalyticsStatCards } from "@/components/analytics/analytics-stat-cards";
import { CollectionRateChart } from "@/components/analytics/collection-rate-chart";
import { FailureFactorsChart } from "@/components/analytics/failure-factors-chart";
import { PredictionAccuracyChart } from "@/components/analytics/prediction-accuracy-chart";
import { RiskDistributionChart } from "@/components/analytics/risk-distribution-chart";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { analyticsApi, type AnalyticsPeriod } from "@/lib/api/analytics";

const PERIOD_OPTIONS: { value: AnalyticsPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "14d", label: "Last 14 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "60d", label: "Last 60 days" },
  { value: "90d", label: "Last 90 days" },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>("30d");

  const { data: summary, loading: loadingSummary, error: summaryError } = useApi(
    () => analyticsApi.summary(period),
    [period],
  );
  const { data: rateData, loading: loadingRate } = useApi(
    () => analyticsApi.collectionRate(period),
    [period],
  );
  const { data: factorsData, loading: loadingFactors } = useApi(
    () => analyticsApi.factors(period),
    [period],
  );

  const loading = loadingSummary || loadingRate || loadingFactors;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-end">
        <Select value={period} onValueChange={(v) => setPeriod(v as AnalyticsPeriod)}>
          <SelectTrigger className="h-9 w-[160px] text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {summaryError ? (
        <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
          Failed to load analytics: {summaryError}
        </div>
      ) : loading && !summary ? (
        <>
          <LoadingSkeleton variant="cards" count={4} />
          <LoadingSkeleton variant="chart" count={4} />
        </>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <CollectionRateChart data={rateData?.data_points ?? []} />
            {summary && <RiskDistributionChart data={summary.risk_distribution} />}
            {summary && <PredictionAccuracyChart data={summary.prediction_accuracy} />}
            <FailureFactorsChart data={factorsData?.factors ?? []} />
          </div>

          {summary && <AnalyticsStatCards summary={summary} />}
        </>
      )}
    </div>
  );
}
