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
  index: number;
  onClick: () => void;
}

export function CollectionsTableRow({ collection, index, onClick }: CollectionsTableRowProps) {
  const due = formatRelativeDate(collection.collection_due_date);

  return (
    <TableRow
      onClick={onClick}
      className={cn(
        "cursor-pointer transition-colors hover:bg-accent/40",
        index % 2 === 0 ? "bg-transparent" : "bg-muted/30",
      )}
    >
      <TableCell className="font-mono text-xs text-muted-foreground">
        {collection.external_collection_id}
      </TableCell>
      <TableCell className="text-sm font-medium text-foreground">
        {collection.external_customer_id}
      </TableCell>
      <TableCell>
        <RiskScoreDisplay score={collection.score} riskLevel={collection.risk_level} />
      </TableCell>
      <TableCell>
        <MethodBadge method={collection.collection_method} />
      </TableCell>
      <TableCell className="text-right font-mono text-sm font-semibold tabular-nums text-foreground">
        {formatCurrency(collection.collection_amount, collection.collection_currency)}
      </TableCell>
      <TableCell>
        <p className="text-sm text-foreground">{formatDate(collection.collection_due_date)}</p>
        <p
          className={cn(
            "mt-0.5 text-xs",
            due.urgent ? "font-medium text-red-400" : "text-muted-foreground",
          )}
        >
          {due.text}
        </p>
      </TableCell>
    </TableRow>
  );
}
