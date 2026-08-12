"use client";

import { HistoryIcon } from "lucide-react";
import { useState } from "react";
import { DataTablePagination } from "@/components/shared/data-table-pagination";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import { configApi } from "@/lib/api/config";
import type { WeightChangeLogEntry } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatDateTime, formatRelativeTime } from "@/lib/utils/format-date";

const PAGE_SIZE = 25;

/**
 * Admin-only compliance audit trail: every weight-tuning change on
 * this tenant, most-recent-first. Backend endpoint is admin-gated;
 * the parent conditionally renders this component so non-admins
 * never see the fetch attempt.
 */
export function WeightHistoryTable() {
  const [page, setPage] = useState(1);
  const { data, loading, error } = useApi(
    () =>
      configApi.getWeightsHistory({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
    [page],
  );

  if (error) {
    return (
      <p className="py-4 text-sm text-muted-foreground">
        Could not load change history: {error}
      </p>
    );
  }

  if (loading && !data) {
    return <LoadingSkeleton variant="rows" count={5} />;
  }

  if (data && data.items.length === 0) {
    return (
      <EmptyState
        icon={<HistoryIcon className="h-6 w-6" />}
        title="No weight changes recorded yet"
        description="When you tune a factor slider and save, the change appears here with the actor, method, factor, and old/new values."
        size="sm"
      />
    );
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="overflow-hidden rounded-md border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>When</TableHead>
            <TableHead>Who</TableHead>
            <TableHead>Method</TableHead>
            <TableHead>Factor</TableHead>
            <TableHead className="text-right">Change</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.items.map((entry) => (
            <HistoryRow key={entry.id} entry={entry} />
          ))}
        </TableBody>
      </Table>
      {data && (
        <div className="border-t border-border">
          <DataTablePagination
            currentPage={page}
            totalPages={totalPages}
            totalItems={data.total}
            pageSize={PAGE_SIZE}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}

function HistoryRow({ entry }: { entry: WeightChangeLogEntry }) {
  return (
    <TableRow>
      <TableCell className="py-2.5 text-sm text-muted-foreground">
        <span title={formatDateTime(entry.changed_at)}>
          {formatRelativeTime(entry.changed_at)}
        </span>
      </TableCell>
      <TableCell className="py-2.5 text-sm">
        <span className="text-foreground">{entry.actor_name ?? "Unknown"}</span>
        {entry.actor_type === "api_key" && (
          <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            API key
          </span>
        )}
      </TableCell>
      <TableCell className="py-2.5 text-sm text-foreground">
        {entry.method_label}
      </TableCell>
      <TableCell className="py-2.5 text-sm text-foreground">
        {entry.factor_label}
      </TableCell>
      <TableCell className="py-2.5 text-right">
        <WeightDelta entry={entry} />
      </TableCell>
    </TableRow>
  );
}

function WeightDelta({ entry }: { entry: WeightChangeLogEntry }) {
  const { old_weight, new_weight, context } = entry;
  const oldStr = old_weight != null ? formatWeight(old_weight) : "–";
  const newStr = new_weight != null ? formatWeight(new_weight) : "–";

  // Colour the new value based on the direction of change so a scanner
  // sees at a glance whether the tenant amplified or dampened a factor.
  let newClass = "text-foreground";
  if (old_weight != null && new_weight != null) {
    if (new_weight > old_weight) newClass = "text-risk-high-fg";
    else if (new_weight < old_weight) newClass = "text-risk-med-fg";
  } else if (old_weight == null && new_weight != null) {
    newClass = "text-risk-low-fg";
  } else if (new_weight == null) {
    newClass = "text-muted-foreground line-through";
  }

  return (
    <span className="font-mono text-xs tabular-nums">
      <span
        className={cn(
          "text-muted-foreground",
          new_weight == null && "line-through",
        )}
      >
        {oldStr}
      </span>
      <span className="mx-1.5 text-muted-foreground">→</span>
      <span className={cn("font-semibold", newClass)}>{newStr}</span>
      {context === "add_method" && (
        <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          new
        </span>
      )}
      {context === "stale_cleanup" && (
        <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          removed
        </span>
      )}
    </span>
  );
}

function formatWeight(w: number): string {
  return w.toFixed(2);
}
