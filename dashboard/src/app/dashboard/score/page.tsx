"use client";

import { AlertCircleIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExampleDataCard } from "@/components/score/example-data-card";
import { ScoredRowsTable } from "@/components/score/scored-rows-table";
import { SingleCollectionForm } from "@/components/score/single-collection-form";
import { SingleScoreResult } from "@/components/score/single-score-result";
import { CsvUploadZone } from "@/components/shared/csv-upload-zone";
import { StatCard } from "@/components/shared/stat-card";
import { useAuth } from "@/hooks/use-auth";
import {
  scoresApi,
  type ScoredUploadRow,
  type ScoresUploadResponse,
} from "@/lib/api/scores";
import type { ScoreResponse } from "@/lib/api/types";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

interface CsvError {
  row: number;
  field: string;
  message: string;
}

export default function ScoreUploadPage() {
  const { canManage } = useAuth();
  const [singleResult, setSingleResult] = useState<ScoreResponse | null>(null);
  const [bulkResult, setBulkResult] = useState<ScoresUploadResponse | null>(null);
  const [csvErrors, setCsvErrors] = useState<CsvError[]>([]);

  const handleBulkResult = (data: unknown) => {
    const res = data as ScoresUploadResponse;
    if (res.errors && res.errors.length > 0) {
      setCsvErrors(res.errors);
      setBulkResult(null);
      toast.error(`CSV has ${res.errors.length} validation error(s)`);
      return;
    }
    setCsvErrors([]);
    setBulkResult(res);
    toast.success(`Scored ${res.total_items ?? 0} collections`);
  };

  const resetBulk = () => {
    setBulkResult(null);
    setCsvErrors([]);
  };

  if (!canManage) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Only Admins and Managers can score collections. Ask an admin to grant
          you Manager access if you need to score on behalf of the team.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        <strong className="text-foreground">Score Collections.</strong>{" "}
        Check whether an upcoming collection is likely to succeed. Score one
        at a time using the form, or upload a CSV to score a batch.
      </div>

      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one">Score one</TabsTrigger>
          <TabsTrigger value="csv">Score from CSV</TabsTrigger>
        </TabsList>

        {/* Single collection */}
        <TabsContent value="one" className="space-y-4">
          {singleResult ? (
            <SingleScoreResult
              result={singleResult}
              onReset={() => setSingleResult(null)}
            />
          ) : (
            <SingleCollectionForm onScored={setSingleResult} />
          )}
        </TabsContent>

        {/* Bulk CSV */}
        <TabsContent value="csv" className="space-y-4">
          {!bulkResult && (
            <CsvUploadZone
              onUpload={scoresApi.uploadCsv}
              onResult={handleBulkResult}
              onError={(msg) => toast.error(msg)}
              templateUrl={scoresApi.templateUrl()}
              requiredColumns={[
                "customer_id",
                "collection_id",
                "collection_amount",
                "collection_currency",
                "collection_due_date",
                "collection_method",
              ]}
              optionalColumns={[
                "total_payments",
                "successful_payments",
                "last_successful_payment_date",
                "average_collection_amount",
                "instalment_number",
                "total_instalments",
                "card_type",
                "card_expiry",
                "last_decline_code",
                "debit_order_returns",
                "known_salary_day",
                "wallet_balance_7d_avg",
                "wallet_balance_current",
                "hours_since_last_inflow",
                "regular_inflow_day",
                "active_loan_count",
                "transactions_last_7d",
                "transactions_avg_7d",
                "last_airtime_purchase_days_ago",
                "new_loan_within_repayment_period",
                "loans_taken_last_90d",
              ]}
              sizeHint="Max 500 rows, 5MB."
            />
          )}

          {!bulkResult && <ExampleDataCard />}

          {csvErrors.length > 0 && (
            <Card className="border-red-500/30 bg-red-50 dark:bg-red-950/20">
              <CardContent className="p-4">
                <p className="text-sm font-medium text-red-700 dark:text-red-400 mb-2">
                  {csvErrors.length} validation error
                  {csvErrors.length > 1 ? "s" : ""} found:
                </p>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {csvErrors.map((err, i) => (
                    <p
                      key={i}
                      className="text-xs text-red-600 dark:text-red-400/80 font-mono"
                    >
                      Row {err.row}
                      {err.field ? `, ${err.field}` : ""}: {err.message}
                    </p>
                  ))}
                </div>
                <button
                  onClick={resetBulk}
                  className="mt-3 text-xs text-muted-foreground hover:text-foreground"
                >
                  Dismiss
                </button>
              </CardContent>
            </Card>
          )}

          {bulkResult && bulkResult.summary && (
            <>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  title="Scored"
                  value={(bulkResult.total_items ?? 0).toLocaleString()}
                />
                <StatCard
                  title="High risk"
                  value={bulkResult.summary.high_risk}
                  accentColor="border-l-red-500"
                  subtitle={formatCompactCurrency(
                    bulkResult.summary.total_value_at_risk,
                    "ZAR",
                  )}
                />
                <StatCard
                  title="Medium risk"
                  value={bulkResult.summary.medium_risk}
                  accentColor="border-l-amber-500"
                />
                <StatCard
                  title="Low risk"
                  value={bulkResult.summary.low_risk}
                  accentColor="border-l-emerald-500"
                />
              </div>

              {bulkResult.results && bulkResult.results.length > 0 && (
                <>
                  <LimitedDataBanner rows={bulkResult.results} />
                  <ScoredRowsTable rows={bulkResult.results} />
                </>
              )}

              <Card>
                <CardContent className="flex flex-col items-start gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      Need more detail? Open these rows on the main dashboard.
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Filter by risk level, sort by score, and open a row for
                      the factor breakdown.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={resetBulk}>
                      Upload another
                    </Button>
                    <Link
                      href="/dashboard"
                      className={buttonVariants({ size: "sm" })}
                    >
                      View on dashboard
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Heuristic: a row is "thin" if the lender populated < 3 optional customer_data
// fields. When most of the upload is thin, scores are mostly factor defaults —
// the lender should know that before acting on a "MEDIUM" risk label.
const THIN_ROW_THRESHOLD = 3;
const THIN_UPLOAD_RATIO = 0.5;

function LimitedDataBanner({ rows }: { rows: ScoredUploadRow[] }) {
  const thin = rows.filter(
    (r) => r.populated_optional_fields < THIN_ROW_THRESHOLD,
  );
  if (thin.length / rows.length < THIN_UPLOAD_RATIO) return null;

  return (
    <Card className="border-amber-500/40 bg-amber-50 dark:bg-amber-950/20">
      <CardContent className="flex gap-3 p-4">
        <AlertCircleIcon className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
        <div className="space-y-1">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
            {thin.length} of {rows.length} rows scored with limited customer data.
          </p>
          <p className="text-xs text-amber-700/90 dark:text-amber-200/80">
            These rows fall back to moderate defaults for most factors, so the
            score reflects {"“"}unknown{"“"} more than risk. Add fields like{" "}
            <span className="font-mono">total_payments</span>,{" "}
            <span className="font-mono">successful_payments</span>,{" "}
            <span className="font-mono">card_expiry</span>, and{" "}
            <span className="font-mono">known_salary_day</span> to your CSV to
            sharpen the prediction — see the Example data card for realistic
            values.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
