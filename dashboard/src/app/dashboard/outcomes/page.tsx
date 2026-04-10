"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { OutcomesFilterTabs } from "@/components/outcomes/outcomes-filter-tabs";
import { OutcomesStats } from "@/components/outcomes/outcomes-stats";
import { OutcomesTable } from "@/components/outcomes/outcomes-table";
import { DataTablePagination } from "@/components/shared/data-table-pagination";
import { PageHeader } from "@/components/shared/page-header";
import type { Outcome, OutcomeFilter, OutcomeStats } from "@/lib/api/types";
import { mockOutcomes } from "@/lib/mock-data";

const PAGE_SIZE = 10;

function computeStats(outcomes: Outcome[]): OutcomeStats {
  const total = outcomes.length;
  const success = outcomes.filter((o) => o.outcome === "SUCCESS").length;
  const pending = outcomes.filter((o) => o.outcome === "PENDING").length;
  const resolved = outcomes.filter((o) => o.outcome !== "PENDING");

  let matched = 0;
  let mismatched = 0;
  for (const o of resolved) {
    if (!o.predicted_risk_level) continue;
    const predictedFailure = o.predicted_risk_level === "HIGH";
    const actuallyFailed = o.outcome === "FAILED";
    if (predictedFailure === actuallyFailed) matched++;
    else mismatched++;
  }

  return {
    total_reported: total,
    collection_rate: total - pending > 0 ? success / (total - pending) : 0,
    matched,
    mismatched,
    pending,
  };
}

function applyFilter(outcomes: Outcome[], filter: OutcomeFilter): Outcome[] {
  if (filter === "ALL") return outcomes;
  if (filter === "PENDING") return outcomes.filter((o) => o.outcome === "PENDING");

  return outcomes.filter((o) => {
    if (o.outcome === "PENDING" || !o.predicted_risk_level) return false;
    const predictedFailure = o.predicted_risk_level === "HIGH";
    const actuallyFailed = o.outcome === "FAILED";
    const isMatched = predictedFailure === actuallyFailed;
    return filter === "MATCHED" ? isMatched : !isMatched;
  });
}

export default function OutcomesPage() {
  const [filter, setFilter] = useState<OutcomeFilter>("ALL");
  const [page, setPage] = useState(1);

  const stats = useMemo(() => computeStats(mockOutcomes), []);
  const filtered = useMemo(() => applyFilter(mockOutcomes, filter), [filter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Outcomes"
        description="Reported collection results — green ✓ means our prediction matched reality"
      />

      <OutcomesStats stats={stats} />

      <Card className="overflow-hidden p-0">
        <div className="border-b border-border p-4">
          <OutcomesFilterTabs
            value={filter}
            onChange={(v) => {
              setFilter(v);
              setPage(1);
            }}
          />
        </div>
        <OutcomesTable outcomes={paged} />
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
    </div>
  );
}
