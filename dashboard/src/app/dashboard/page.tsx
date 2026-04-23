"use client";

import { useMemo, useState } from "react";
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
import type { Collection } from "@/lib/api/types";
import type { CollectionMethod } from "@/lib/utils/format-method";
import type { RiskLevel } from "@/lib/utils/format-risk";
import { mockCollections } from "@/lib/mock-data";

const PAGE_SIZE = 10;

const DATE_RANGE_DAYS: Record<DateRangeFilter, number> = {
  today: 0,
  "3d": 3,
  "7d": 7,
  "14d": 14,
  "30d": 30,
};

export default function DashboardPage() {
  const [riskFilter, setRiskFilter] = useState<RiskLevel | null>(null);
  const [methodFilter, setMethodFilter] = useState<CollectionMethod | "ALL">("ALL");
  const [dateRange, setDateRange] = useState<DateRangeFilter>("7d");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<CollectionsSortField>("score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selected, setSelected] = useState<Collection | null>(null);

  const filtered = useMemo(() => {
    const now = new Date();
    const maxDays = DATE_RANGE_DAYS[dateRange];
    return mockCollections
      .filter((c) => (riskFilter ? c.risk_level === riskFilter : true))
      .filter((c) => (methodFilter !== "ALL" ? c.collection_method === methodFilter : true))
      .filter((c) => {
        const due = new Date(c.collection_due_date);
        const diffDays = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        // Show items due within the window (including overdue)
        return diffDays <= maxDays;
      })
      .filter((c) => {
        if (!search.trim()) return true;
        const q = search.toLowerCase();
        return (
          c.external_customer_id.toLowerCase().includes(q) ||
          c.external_collection_id.toLowerCase().includes(q)
        );
      });
  }, [riskFilter, methodFilter, dateRange, search]);

  const sorted = useMemo(() => {
    const items = [...filtered];
    items.sort((a, b) => {
      let cmp = 0;
      if (sortField === "score") {
        cmp = a.score - b.score;
      } else {
        cmp =
          new Date(a.collection_due_date).getTime() -
          new Date(b.collection_due_date).getTime();
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });
    return items;
  }, [filtered, sortField, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = sorted.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const handleSortChange = (field: CollectionsSortField) => {
    if (field === sortField) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  return (
    <div className="space-y-6">
      <SummaryCards
        collections={mockCollections}
        activeFilter={riskFilter}
        onFilterChange={(f) => {
          setRiskFilter(f);
          setPage(1);
        }}
      />

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
        <CollectionsTable
          collections={paged}
          onRowClick={setSelected}
          sortField={sortField}
          sortDirection={sortDirection}
          onSortChange={handleSortChange}
        />
        <div className="border-t border-border">
          <DataTablePagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={sorted.length}
            pageSize={PAGE_SIZE}
            onPageChange={setPage}
          />
        </div>
      </Card>

      <RiskDetailDrawer
        collection={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
