"use client";

import { TableCell, TableRow } from "@/components/ui/table";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { Collection } from "@/lib/api/types";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatRelativeDate } from "@/lib/utils/format-date";
import { cn } from "@/lib/utils";

interface CollectionsTableRowProps {
  collection: Collection;
  onClick: () => void;
}

export function CollectionsTableRow({ collection, onClick }: CollectionsTableRowProps) {
  const due = formatRelativeDate(collection.collection_due_date);

  return (
    <TableRow
      onClick={onClick}
      className="cursor-pointer hover:bg-accent/40"
    >
      <TableCell className="font-mono text-xs text-muted-foreground">
        {collection.external_collection_id}
      </TableCell>
      <TableCell className="font-medium">{collection.external_customer_id}</TableCell>
      <TableCell>
        <RiskScoreDisplay score={collection.score} riskLevel={collection.risk_level} />
      </TableCell>
      <TableCell>
        <MethodBadge method={collection.collection_method} />
      </TableCell>
      <TableCell className="font-mono tabular-nums">
        {formatCurrency(collection.collection_amount, collection.collection_currency)}
      </TableCell>
      <TableCell>
        <span className={cn(due.urgent && "text-amber-400 font-medium")}>{due.text}</span>
      </TableCell>
    </TableRow>
  );
}
