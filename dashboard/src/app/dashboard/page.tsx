"use client";

import { useCallback, useState } from "react";
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
};

export default function DashboardPage() {
  const [riskFilter, setRiskFilter] = useState<RiskLevel | null>(null);
  const [methodFilter, setMethodFilter] = useState<CollectionMethod | "ALL">("ALL");
  const [dateRange, setDateRange] = useState<DateRangeFilter>("30d");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<CollectionsSortField>("score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedId, setSelectedId] = useState<string | null>(null);

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
      setSortDirection("desc");
    }
  };

  const handleRowClick = useCallback((item: ScoreListItem) => {
    setSelectedId(item.score_id);
  }, []);

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
