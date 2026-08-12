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
import type { ActivityLogEntry } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatDateTime, formatRelativeTime } from "@/lib/utils/format-date";

const PAGE_SIZE = 25;

// Plain-English labels for entity_type + action. Kept inline (not a
// shared constant) because these values only surface here — no other
// component renders them and centralising would just move the
// mapping without eliminating it.
const ENTITY_LABEL: Record<string, string> = {
  user: "Team member",
  api_key: "API key",
  alert_config: "Alerts",
  webhook_secret: "Webhook secret",
  outcome: "Outcome",
};

const ACTION_LABEL: Record<string, string> = {
  create: "Created",
  update: "Updated",
  delete: "Deleted",
  revoke: "Revoked",
  activate: "Activated",
  deactivate: "Deactivated",
  rotate: "Rotated",
};

/**
 * Admin-only compliance audit trail covering everything EXCEPT weight
 * tuning (which has its own dedicated `<WeightHistoryTable>` on the
 * Weights tab). Parent conditionally renders this so non-admins
 * never see the fetch attempt.
 */
export function ActivityTable() {
  const [page, setPage] = useState(1);
  const { data, loading, error } = useApi(
    () =>
      configApi.getActivity({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
    [page],
  );

  if (error) {
    return (
      <p className="py-4 text-sm text-muted-foreground">
        Could not load activity: {error}
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
        title="No activity recorded yet"
        description="When someone changes a team role, toggles an API key, updates alert settings, rotates the webhook secret, or deletes an outcome, the change appears here."
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
            <TableHead>Entity</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Change</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.items.map((entry) => (
            <ActivityRow key={entry.id} entry={entry} />
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

function ActivityRow({ entry }: { entry: ActivityLogEntry }) {
  return (
    <TableRow>
      <TableCell className="py-2.5 text-sm text-muted-foreground">
        <span title={formatDateTime(entry.created_at)}>
          {formatRelativeTime(entry.created_at)}
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
        {ENTITY_LABEL[entry.entity_type] ?? entry.entity_type}
      </TableCell>
      <TableCell className="py-2.5 text-sm text-foreground">
        {ACTION_LABEL[entry.action] ?? entry.action}
      </TableCell>
      <TableCell className="py-2.5 text-sm">
        <ChangeCell entry={entry} />
      </TableCell>
    </TableRow>
  );
}

function ChangeCell({ entry }: { entry: ActivityLogEntry }) {
  // No values captured (webhook secret rotation, generic events) —
  // the action word itself is the change.
  if (!entry.before && !entry.after) {
    return (
      <span className="text-xs text-muted-foreground">
        {entry.action === "rotate" ? "Secret rotated" : "–"}
      </span>
    );
  }

  // Create — show the after snapshot summarised.
  if (!entry.before && entry.after) {
    return (
      <SummaryChip data={entry.after} tone="new" />
    );
  }

  // Delete / revoke — show the before snapshot struck through.
  if (entry.before && !entry.after) {
    return (
      <SummaryChip data={entry.before} tone="removed" />
    );
  }

  // Update — show per-field before -> after.
  return (
    <div className="space-y-0.5 text-xs">
      {Object.keys(entry.before ?? {}).map((key) => (
        <FieldDiff
          key={key}
          field={key}
          before={entry.before?.[key]}
          after={entry.after?.[key]}
        />
      ))}
    </div>
  );
}

function SummaryChip({
  data,
  tone,
}: {
  data: Record<string, unknown>;
  tone: "new" | "removed";
}) {
  // Show the two most-useful fields per entity: name/label/collection_id/role.
  // Falls back to enumerating everything if none match.
  const preferred = ["name", "email", "label", "prefix", "role", "collection_id"];
  const shown: [string, unknown][] = [];
  for (const k of preferred) {
    if (k in data) shown.push([k, data[k]]);
  }
  if (shown.length === 0) {
    for (const [k, v] of Object.entries(data).slice(0, 3)) {
      shown.push([k, v]);
    }
  }

  return (
    <span
      className={cn(
        "font-mono text-xs",
        tone === "removed" && "text-muted-foreground line-through",
      )}
    >
      {shown.map(([k, v]) => `${k}=${formatValue(v)}`).join(" · ")}
    </span>
  );
}

function FieldDiff({
  field,
  before,
  after,
}: {
  field: string;
  before: unknown;
  after: unknown;
}) {
  return (
    <div className="font-mono">
      <span className="text-muted-foreground">{field}: </span>
      <span className="text-muted-foreground">{formatValue(before)}</span>
      <span className="mx-1.5 text-muted-foreground">→</span>
      <span className="font-semibold text-foreground">{formatValue(after)}</span>
    </div>
  );
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "string") return v.length > 40 ? v.slice(0, 40) + "…" : v;
  if (typeof v === "boolean") return v ? "true" : "false";
  if (Array.isArray(v)) return `[${v.length}]`;
  return String(v);
}
