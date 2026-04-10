"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { CollectionsTable } from "@/components/dashboard/collections-table";
import { CollectionsToolbar } from "@/components/dashboard/collections-toolbar";
import { RiskDetailDrawer } from "@/components/dashboard/risk-detail-drawer";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { DataTablePagination } from "@/components/shared/data-table-pagination";
import { PageHeader } from "@/components/shared/page-header";
import type { Collection } from "@/lib/api/types";
import type { CollectionMethod } from "@/lib/utils/format-method";
import type { RiskLevel } from "@/lib/utils/format-risk";
import { mockCollections } from "@/lib/mock-data";

const PAGE_SIZE = 10;

export default function DashboardPage() {
  const [riskFilter, setRiskFilter] = useState<RiskLevel | null>(null);
  const [methodFilter, setMethodFilter] = useState<CollectionMethod | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Collection | null>(null);

  const filtered = useMemo(() => {
    return mockCollections
      .filter((c) => (riskFilter ? c.risk_level === riskFilter : true))
      .filter((c) => (methodFilter !== "ALL" ? c.collection_method === methodFilter : true))
      .filter((c) => {
        if (!search.trim()) return true;
        const q = search.toLowerCase();
        return (
          c.external_customer_id.toLowerCase().includes(q) ||
          c.external_collection_id.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => b.score - a.score);
  }, [riskFilter, methodFilter, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Risk-ranked upcoming collections — click any row for full breakdown"
      />

      <SummaryCards
        collections={mockCollections}
        activeFilter={riskFilter}
        onFilterChange={(f) => {
          setRiskFilter(f);
          setPage(1);
        }}
      />

      <Card className="overflow-hidden p-0">
        <div className="border-b border-border p-4">
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
          />
        </div>
        <CollectionsTable collections={paged} onRowClick={setSelected} />
        <div className="border-t border-border">
          <DataTablePagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={filtered.length}
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
