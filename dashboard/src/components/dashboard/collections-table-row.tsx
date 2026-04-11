"use client";

import { TableCell, TableRow } from "@/components/ui/table";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { Collection } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate, formatRelativeDate } from "@/lib/utils/format-date";

interface CollectionsTableRowProps {
  collection: Collection;
  onClick: () => void;
}

// Derive market label from currency. ZAR=SA, ZMW=ZM.
function marketLabel(currency: Collection["collection_currency"]): string {
  return currency === "ZAR" ? "SA" : "ZM";
}

export function CollectionsTableRow({ collection, onClick }: CollectionsTableRowProps) {
  const due = formatRelativeDate(collection.collection_due_date);
  const isOverdue = due.text === "Overdue";

  const instalmentNumber = collection.customer_data.instalment_number ?? null;
  const totalInstalments = collection.customer_data.total_instalments ?? null;
  const showInstalment = instalmentNumber !== null && totalInstalments !== null && totalInstalments > 0;
  const instalmentPct = showInstalment
    ? Math.min(100, Math.round((instalmentNumber! / totalInstalments!) * 100))
    : 0;

  return (
    <TableRow
      onClick={onClick}
      className="cursor-pointer border-b border-border/50 transition-colors hover:bg-accent/40"
    >
      <TableCell className="py-3">
        <RiskScoreDisplay score={collection.score} riskLevel={collection.risk_level} />
      </TableCell>
      <TableCell className="py-3">
        <span className="block text-sm font-medium text-foreground">
          {collection.external_customer_id}
        </span>
        <span className="mt-0.5 block text-xs text-muted-foreground">
          {marketLabel(collection.collection_currency)}
        </span>
      </TableCell>
      <TableCell className="py-3 text-right font-mono text-sm font-semibold tabular-nums text-foreground">
        {formatCurrency(collection.collection_amount, collection.collection_currency)}
      </TableCell>
      <TableCell className="py-3">
        <span className="block text-sm text-foreground">
          {formatDate(collection.collection_due_date)}
        </span>
        <span
          className={cn(
            "mt-0.5 block text-xs",
            isOverdue
              ? "font-medium text-red-400"
              : due.urgent
                ? "font-medium text-amber-400"
                : "text-muted-foreground",
          )}
        >
          {due.text}
        </span>
      </TableCell>
      <TableCell className="py-3">
        {showInstalment ? (
          <div className="flex flex-col items-start gap-1">
            <span className="text-sm text-foreground">
              {instalmentNumber} of {totalInstalments}
            </span>
            <div className="h-1 w-16 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-emerald-500"
                style={{ width: `${instalmentPct}%` }}
              />
            </div>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="py-3">
        <MethodBadge method={collection.collection_method} />
      </TableCell>
      <TableCell className="py-3 text-right">
        <span className="text-sm text-muted-foreground transition-colors group-hover:text-foreground">
          Details
        </span>
      </TableCell>
    </TableRow>
  );
}
