"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CsvUploadZone } from "@/components/shared/csv-upload-zone";
import { StatCard } from "@/components/shared/stat-card";
import { useAuth } from "@/hooks/use-auth";
import { scoresApi, type ScoresUploadResponse } from "@/lib/api/scores";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

interface CsvError {
  row: number;
  field: string;
  message: string;
}

export default function ScoreUploadPage() {
  const { canManage } = useAuth();
  const [result, setResult] = useState<ScoresUploadResponse | null>(null);
  const [csvErrors, setCsvErrors] = useState<CsvError[]>([]);

  const handleResult = (data: unknown) => {
    const res = data as ScoresUploadResponse;
    if (res.errors && res.errors.length > 0) {
      setCsvErrors(res.errors);
      setResult(null);
      toast.error(`CSV has ${res.errors.length} validation error(s)`);
      return;
    }
    setCsvErrors([]);
    setResult(res);
    toast.success(`Scored ${res.total_items ?? 0} collections`);
  };

  const reset = () => {
    setResult(null);
    setCsvErrors([]);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        <strong className="text-foreground">Score Collections.</strong>{" "}
        Upload a CSV of your upcoming collections — we score every row through
        the same engine the API uses, persist the results, and the scored
        rows appear on the main dashboard for triage. Useful for batch
        scoring before a debit run or when piloting without an API
        integration.
      </div>

      {!result && canManage && (
        <CsvUploadZone
          onUpload={scoresApi.uploadCsv}
          onResult={handleResult}
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
            "instalment_number",
            "total_instalments",
            "card_type",
            "card_expiry",
          ]}
          sizeHint="Max 500 rows, 5MB."
        />
      )}

      {!result && !canManage && (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground">
            Only Admins and Managers can upload collections for scoring.
          </CardContent>
        </Card>
      )}

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
              onClick={reset}
              className="mt-3 text-xs text-muted-foreground hover:text-foreground"
            >
              Dismiss
            </button>
          </CardContent>
        </Card>
      )}

      {result && result.summary && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Scored"
              value={(result.total_items ?? 0).toLocaleString()}
            />
            <StatCard
              title="High risk"
              value={result.summary.high_risk}
              accentColor="border-l-red-500"
              subtitle={formatCompactCurrency(
                result.summary.total_value_at_risk,
                "ZAR",
              )}
            />
            <StatCard
              title="Medium risk"
              value={result.summary.medium_risk}
              accentColor="border-l-amber-500"
            />
            <StatCard
              title="Low risk"
              value={result.summary.low_risk}
              accentColor="border-l-emerald-500"
            />
          </div>

          <Card>
            <CardContent className="flex flex-col items-start gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">
                  Scored rows are now on the main dashboard.
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Filter by risk level, sort by score, and open a row for the
                  factor breakdown.
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={reset}>
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
    </div>
  );
}
