"use client";

import { CheckCircle2Icon, XCircleIcon } from "lucide-react";
import { TableCell, TableRow } from "@/components/ui/table";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { OutcomeListItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDateTime, formatRelativeTime } from "@/lib/utils/format-date";

interface OutcomesTableRowProps {
  outcome: OutcomeListItem;
}

const OUTCOME_BADGE: Record<string, { label: string; className: string }> = {
  SUCCESS: {
    label: "Success",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  FAILED: {
    label: "Failed",
    className: "bg-red-500/10 text-red-400 border-red-500/30",
  },
};

function MatchCell({ matched }: { matched: boolean | null }) {
  if (matched === true) {
    return <CheckCircle2Icon className="mx-auto h-4 w-4 text-emerald-400" />;
  }
  if (matched === false) {
    return <XCircleIcon className="mx-auto h-4 w-4 text-red-400" />;
  }
  return <span className="text-xs text-muted-foreground">—</span>;
}

export function OutcomesTableRow({ outcome }: OutcomesTableRowProps) {
  const badge = OUTCOME_BADGE[outcome.outcome] ?? OUTCOME_BADGE.FAILED;

  return (
    <TableRow className="border-b border-border/50 transition-colors hover:bg-accent/40">
      <TableCell className="py-3 font-mono text-sm text-muted-foreground">
        {outcome.external_collection_id}
      </TableCell>
      <TableCell className="py-3">
        {outcome.score !== null && outcome.risk_level ? (
          <RiskScoreDisplay
            score={outcome.score}
            riskLevel={outcome.risk_level}
            showBar={false}
          />
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="py-3">
        <span
          className={cn(
            "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
            badge.className,
          )}
        >
          {badge.label}
        </span>
      </TableCell>
      <TableCell className="py-3 text-sm text-muted-foreground">
        {outcome.failure_reason ?? "—"}
      </TableCell>
      <TableCell className="py-3 text-right font-mono text-sm font-semibold tabular-nums text-foreground">
        {outcome.collection_amount && outcome.collection_currency
          ? formatCurrency(outcome.collection_amount, outcome.collection_currency)
          : "—"}
      </TableCell>
      <TableCell className="py-3 text-sm text-muted-foreground">
        {formatDateTime(outcome.attempted_at)}
      </TableCell>
      <TableCell className="py-3 text-sm text-muted-foreground/80">
        {formatRelativeTime(outcome.reported_at)}
      </TableCell>
      <TableCell className="py-3 text-center">
        <MatchCell matched={outcome.prediction_matched} />
      </TableCell>
    </TableRow>
  );
}
