"use client";

import { ArrowRightIcon, BarChart3Icon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { AnalyticsStatCards } from "@/components/analytics/analytics-stat-cards";
import { CollectionRateChart } from "@/components/analytics/collection-rate-chart";
import { FailureFactorsChart } from "@/components/analytics/failure-factors-chart";
import { PredictionAccuracyChart } from "@/components/analytics/prediction-accuracy-chart";
import { RiskDistributionChart } from "@/components/analytics/risk-distribution-chart";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { analyticsApi, type AnalyticsPeriod } from "@/lib/api/analytics";

// Match the muted-outline link button used on other empty states so a
// non-tech clerk sees the same click affordance everywhere.
const LINK_BUTTON_CLS =
  "inline-flex h-7 items-center gap-1.5 rounded-[12px] border border-border bg-background px-2.5 text-[0.8rem] font-medium text-foreground transition-colors hover:bg-muted dark:border-input dark:bg-input/30 dark:hover:bg-input/50";

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
      <PageHeader
        title="Analytics"
        subtitle="Collection performance and prediction accuracy"
        action={
          <Select value={period} onValueChange={(v) => setPeriod(v as AnalyticsPeriod)}>
            <SelectTrigger className="w-[160px] text-sm">
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
        }
      />

      {summaryError ? (
        <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
          Failed to load analytics: {summaryError}
        </div>
      ) : loading && !summary ? (
        <>
          <LoadingSkeleton variant="cards" count={4} />
          <LoadingSkeleton variant="chart" count={4} />
        </>
      ) : summary && summary.total_scored === 0 ? (
        // First-time empty state: rendering charts with all-zero values reads
        // as "the product is broken." Say what will show up here instead.
        <EmptyState
          icon={<BarChart3Icon className="h-6 w-6" />}
          title="No analytics yet"
          description={
            "Once you've scored a few collections and recorded some outcomes, this page will show your collection-rate trend, which factors drive failures, and how often our predictions match reality."
          }
          action={
            <Link href="/dashboard/score" className={LINK_BUTTON_CLS}>
              Score your first collection
              <ArrowRightIcon className="h-3.5 w-3.5" />
            </Link>
          }
        />
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
