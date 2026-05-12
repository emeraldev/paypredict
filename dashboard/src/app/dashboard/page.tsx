"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import {
  CollectionsTable,
  type CollectionsSortField,
  type SortDirection,
} from "@/components/dashboard/collections-table";
import {
  CollectionsToolbar,
  type DateRangeFilter,
} from "@/components/dashboard/collections-toolbar";
import { RiskDetailDrawer } from "@/components/dashboard/risk-detail-drawer";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { DataTablePagination } from "@/components/shared/data-table-pagination";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { scoresApi } from "@/lib/api/scores";
import type { CollectionsListParams, ScoreDetailResponse, ScoreListItem } from "@/lib/api/types";
import { downloadCsv, fetchAllPages } from "@/lib/utils/csv-export";
import type { CollectionMethod } from "@/lib/utils/format-method";
import type { RiskLevel } from "@/lib/utils/format-risk";
import { addDays, format } from "date-fns";

const PAGE_SIZE = 25;

const DATE_RANGE_DAYS: Record<DateRangeFilter, number> = {
  today: 0,
  "3d": 3,
  "7d": 7,
  "14d": 14,
  "30d": 30,
};

// Map CollectionsSortField to API sort_by
const SORT_MAP: Record<CollectionsSortField, string> = {
  score: "score",
  due_date: "collection_due_date",
  customer: "external_customer_id",
  amount: "collection_amount",
  method: "collection_method",
};

export default function DashboardPage() {
  const searchParams = useSearchParams();
  const [riskFilter, setRiskFilter] = useState<RiskLevel | null>(null);
  const [methodFilter, setMethodFilter] = useState<CollectionMethod | "ALL">("ALL");
  const [dateRange, setDateRange] = useState<DateRangeFilter>("30d");
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<CollectionsSortField>("score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Update search when URL param changes (topbar search submits navigate here)
  useEffect(() => {
    const fromUrl = searchParams.get("search") ?? "";
    setSearch(fromUrl);
    setPage(1);
  }, [searchParams]);

  // Build API params
  const params: CollectionsListParams = {
    page,
    page_size: PAGE_SIZE,
    risk_level: riskFilter,
    collection_method: methodFilter === "ALL" ? null : methodFilter,
    search: search.trim() || undefined,
    sort_by: SORT_MAP[sortField],
    sort_order: sortDirection,
    date_from: format(new Date(), "yyyy-MM-dd"),
    date_to: format(addDays(new Date(), DATE_RANGE_DAYS[dateRange]), "yyyy-MM-dd"),
  };

  const { data, loading, error } = useApi(
    () => scoresApi.list(params),
    [page, riskFilter, methodFilter, dateRange, search, sortField, sortDirection],
  );

  // Fetch detail for drawer
  const { data: detail } = useApi(
    () => (selectedId ? scoresApi.getDetail(selectedId) : Promise.resolve(null)),
    [selectedId],
  );

  const handleSortChange = (field: CollectionsSortField) => {
    if (field === sortField) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection(field === "customer" || field === "method" ? "asc" : "desc");
    }
  };

  const handleRowClick = useCallback((item: ScoreListItem) => {
    setSelectedId(item.score_id);
  }, []);

  const handleExport = async () => {
    try {
      // Fetch ALL pages of the filtered set (capped at 5000 rows for safety)
      const items = await fetchAllPages(
        (page, pageSize) => scoresApi.list({ ...params, page, page_size: pageSize }),
      );
      if (items.length === 0) {
        toast.error("No collections to export");
        return;
      }
      const rows = items.map((s) => ({
        score_id: s.score_id,
        customer_id: s.external_customer_id,
        collection_id: s.external_collection_id,
        amount: s.collection_amount,
        currency: s.collection_currency,
        due_date: s.collection_due_date,
        method: s.collection_method,
        instalment: s.instalment_number != null && s.total_instalments != null
          ? `${s.instalment_number}/${s.total_instalments}`
          : "",
        score: s.score.toFixed(4),
        risk_level: s.risk_level,
        recommended_action: s.recommended_action,
        scored_at: s.scored_at,
      }));
      const today = format(new Date(), "yyyy-MM-dd");
      downloadCsv(`paypredict-collections-${today}.csv`, rows);
      toast.success(`Exported ${rows.length} collections`);
    } catch {
      toast.error("Export failed");
    }
  };

  if (error) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
        Failed to load collections: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {loading && !data ? (
        <LoadingSkeleton variant="cards" count={4} />
      ) : data ? (
        <SummaryCards
          summary={data.summary}
          activeFilter={riskFilter}
          onFilterChange={(f) => {
            setRiskFilter(f);
            setPage(1);
          }}
        />
      ) : null}

      <CollectionsToolbar
        search={search}
        onSearchChange={(v) => {
          setSearch(v);
          setPage(1);
        }}
        method={methodFilter}
        onMethodChange={(v) => {
          setMethodFilter(v);
          setPage(1);
        }}
        dateRange={dateRange}
        onDateRangeChange={(v) => {
          setDateRange(v);
          setPage(1);
        }}
        onExport={handleExport}
      />

      <Card className="overflow-hidden p-0">
        {loading && !data ? (
          <LoadingSkeleton variant="rows" count={10} />
        ) : (
          <>
            <CollectionsTable
              collections={data?.items ?? []}
              onRowClick={handleRowClick}
              sortField={sortField}
              sortDirection={sortDirection}
              onSortChange={handleSortChange}
              hasActiveFilters={
                riskFilter !== null ||
                methodFilter !== "ALL" ||
                dateRange !== "30d" ||
                search.trim().length > 0
              }
              onClearFilters={() => {
                setRiskFilter(null);
                setMethodFilter("ALL");
                setDateRange("30d");
                setSearch("");
                setPage(1);
              }}
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

      <RiskDetailDrawer
        detail={detail as ScoreDetailResponse | null}
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
