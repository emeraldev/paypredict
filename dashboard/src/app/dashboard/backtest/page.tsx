"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BacktestHeadline } from "@/components/backtest/backtest-headline";
import { BacktestResultsTable } from "@/components/backtest/backtest-results-table";
import { CollectionRateComparison } from "@/components/backtest/collection-rate-comparison";
import { ConfusionMatrix } from "@/components/backtest/confusion-matrix";
import { CsvUploadZone } from "@/components/backtest/csv-upload-zone";
import { PastBacktestsList } from "@/components/backtest/past-backtests-list";
import { FailureFactorsChart } from "@/components/analytics/failure-factors-chart";
import { StatCard } from "@/components/shared/stat-card";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { backtestApi } from "@/lib/api/backtest";
import type { BacktestResponse } from "@/lib/api/types";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

export default function BacktestPage() {
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const { data: pastBacktests, loading: loadingPast, refetch } = useApi(
    () => backtestApi.list(),
    [],
  );

  const handleResult = (data: unknown) => {
    const res = data as BacktestResponse;
    // Check if it's a validation error response
    if (res.errors && res.errors.length > 0) {
      toast.error(`CSV has ${res.errors.length} validation error(s)`);
      return;
    }
    setResult(res);
    refetch();
    toast.success("Backtest complete");
  };

  const handleSelectPast = async (id: string) => {
    try {
      const data = await backtestApi.get(id);
      setResult(data);
    } catch {
      toast.error("Failed to load backtest");
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload section */}
      {!result && (
        <CsvUploadZone
          onResult={handleResult}
          onError={(msg) => toast.error(msg)}
        />
      )}

      {/* Results */}
      {result && result.summary && (
        <>
          <BacktestHeadline summary={result.summary} />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Collections Tested"
              value={result.total_collections.toLocaleString()}
            />
            <StatCard
              title="Actual Collection Rate"
              value={`${Math.round(result.summary.collection_rate_actual * 100)}%`}
            />
            <StatCard
              title="Predicted Accuracy"
              value={`${Math.round(result.summary.overall_accuracy * 100)}%`}
            />
            <StatCard
              title="Est. Annual Recovery"
              value={formatCompactCurrency(result.summary.estimated_annual_recovery, "ZAR")}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {result.confusion_matrix && (
              <ConfusionMatrix data={result.confusion_matrix} />
            )}
            <CollectionRateComparison
              actualRate={result.summary.collection_rate_actual}
              projectedRate={result.summary.collection_rate_if_acted}
            />
          </div>

          {result.top_failure_factors && result.top_failure_factors.length > 0 && (
            <FailureFactorsChart
              data={result.top_failure_factors.map((f) => ({
                factor: f.factor,
                avg_contribution: f.contribution,
                correlation_with_failure: f.avg_score_in_failures,
              }))}
            />
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Risk Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <BacktestResultsTable backtest={result} />
            </CardContent>
          </Card>

          {/* Run another */}
          <div className="flex justify-center">
            <button
              onClick={() => setResult(null)}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Run another backtest
            </button>
          </div>
        </>
      )}

      {/* Past backtests */}
      {loadingPast ? (
        <LoadingSkeleton variant="rows" count={3} />
      ) : (
        <PastBacktestsList
          items={pastBacktests?.items ?? []}
          onSelect={handleSelectPast}
        />
      )}
    </div>
  );
}
