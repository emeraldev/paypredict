"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { OutcomesFilterTabs } from "@/components/outcomes/outcomes-filter-tabs";
import { OutcomesStats } from "@/components/outcomes/outcomes-stats";
import { OutcomesTable } from "@/components/outcomes/outcomes-table";
import { DataTablePagination } from "@/components/shared/data-table-pagination";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { outcomesApi } from "@/lib/api/outcomes";
import type { OutcomeFilter, OutcomesListParams } from "@/lib/api/types";

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

  const params: OutcomesListParams = {
    page,
    page_size: PAGE_SIZE,
    sort_by: "attempted_at",
    sort_order: "desc",
    ...filterToParams(filter),
  };

  const { data, loading, error } = useApi(
    () => outcomesApi.list(params),
    [page, filter],
  );

  if (error) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
        Failed to load outcomes: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {loading && !data ? (
        <LoadingSkeleton variant="cards" count={4} />
      ) : data ? (
        <OutcomesStats stats={data.stats} />
      ) : null}

      <OutcomesFilterTabs
        value={filter}
        onChange={(v) => {
          setFilter(v);
          setPage(1);
        }}
      />

      <Card className="overflow-hidden p-0">
        {loading && !data ? (
          <LoadingSkeleton variant="rows" count={10} />
        ) : (
          <>
            <OutcomesTable outcomes={data?.items ?? []} />
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
