"use client";

import { useState } from "react";
import { DownloadIcon, PlusIcon } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ReportOutcomeForm } from "@/components/dashboard/report-outcome-form";
import { OutcomesFilterTabs } from "@/components/outcomes/outcomes-filter-tabs";
import { OutcomesStats } from "@/components/outcomes/outcomes-stats";
import { OutcomesTable } from "@/components/outcomes/outcomes-table";
import { DataTablePagination } from "@/components/shared/data-table-pagination";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { outcomesApi } from "@/lib/api/outcomes";
import type { OutcomeFilter, OutcomesListParams } from "@/lib/api/types";
import { downloadCsv, fetchAllPages } from "@/lib/utils/csv-export";

const PAGE_SIZE = 25;

// Map UI filter tabs to API query params
function filterToParams(filter: OutcomeFilter): Pick<OutcomesListParams, "outcome" | "match"> {
  switch (filter) {
    case "MATCHED":
      return { match: "MATCHED" };
    case "MISMATCHED":
      return { match: "MISMATCHED" };
    default:
      return {};
  }
}

export default function OutcomesPage() {
  const [filter, setFilter] = useState<OutcomeFilter>("ALL");
  const [page, setPage] = useState(1);
  const [reportOpen, setReportOpen] = useState(false);

  const params: OutcomesListParams = {
    page,
    page_size: PAGE_SIZE,
    sort_by: "attempted_at",
    sort_order: "desc",
    ...filterToParams(filter),
  };

  const { data, loading, error, refetch } = useApi(
    () => outcomesApi.list(params),
    [page, filter],
  );

  const handleExport = async () => {
    try {
      const items = await fetchAllPages(
        (p, pageSize) => outcomesApi.list({ ...params, page: p, page_size: pageSize }),
      );
      if (items.length === 0) {
        toast.error("No outcomes to export");
        return;
      }
      const rows = items.map((o) => ({
        outcome_id: o.outcome_id,
        collection_id: o.collection_id,
        outcome: o.outcome,
        failure_reason: o.failure_reason ?? "",
        amount: o.collection_amount ?? "",
        currency: o.collection_currency ?? "",
        method: o.collection_method ?? "",
        predicted_score: o.score != null ? o.score.toFixed(4) : "",
        predicted_risk_level: o.risk_level ?? "",
        prediction_matched: o.prediction_matched == null ? "" : o.prediction_matched ? "yes" : "no",
        attempted_at: o.attempted_at,
        reported_at: o.reported_at,
      }));
      const today = format(new Date(), "yyyy-MM-dd");
      downloadCsv(`paypredict-outcomes-${today}.csv`, rows);
      toast.success(`Exported ${rows.length} outcomes`);
    } catch {
      toast.error("Export failed");
    }
  };

  if (error) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
        Failed to load outcomes: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        After you attempt a collection, record what happened — succeeded or
        failed — so we can compare it against what we predicted. Report
        outcomes here, from the score detail drawer on the main dashboard,
        or via{" "}
        <code className="rounded bg-muted px-1 text-xs">POST /v1/outcomes</code>.
      </div>

      {loading && !data ? (
        <LoadingSkeleton variant="cards" count={4} />
      ) : data ? (
        <OutcomesStats stats={data.stats} />
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <OutcomesFilterTabs
          value={filter}
          onChange={(v) => {
            setFilter(v);
            setPage(1);
          }}
        />
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => setReportOpen(true)}
          >
            <PlusIcon className="h-4 w-4" />
            Report outcome
          </Button>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExport}>
            <DownloadIcon className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Report outcome</DialogTitle>
            <DialogDescription>
              Record what happened when you attempted a collection.
            </DialogDescription>
          </DialogHeader>
          <ReportOutcomeForm
            variant="standalone"
            onReported={() => {
              setReportOpen(false);
              refetch();
            }}
          />
        </DialogContent>
      </Dialog>

      <Card className="overflow-hidden p-0">
        {loading && !data ? (
          <LoadingSkeleton variant="rows" count={10} />
        ) : (
          <>
            <OutcomesTable
              outcomes={data?.items ?? []}
              filter={filter}
              onClearFilter={() => {
                setFilter("ALL");
                setPage(1);
              }}
              onRemoved={refetch}
            />
            {data && (
              <div className="border-t border-border">
                <DataTablePagination
                  currentPage={data.pagination.page}
                  totalPages={data.pagination.total_pages}
                  totalItems={data.pagination.total_items}
                  pageSize={data.pagination.page_size}
                  onPageChange={setPage}
                />
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
