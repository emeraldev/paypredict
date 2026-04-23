"use client";

import { CheckCircle2Icon, XCircleIcon } from "lucide-react";
import { TableCell, TableRow } from "@/components/ui/table";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { Outcome } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDateTime, formatRelativeTime } from "@/lib/utils/format-date";

interface OutcomesTableRowProps {
  outcome: Outcome;
}

type MatchStatus = "matched" | "mismatched" | "pending";

function outcomeMatchesPrediction(outcome: Outcome): MatchStatus {
  if (outcome.outcome === "PENDING") return "pending";
  if (!outcome.predicted_risk_level) return "pending";
  const predictedFailure = outcome.predicted_risk_level === "HIGH";
  const actuallyFailed = outcome.outcome === "FAILED";
  return predictedFailure === actuallyFailed ? "matched" : "mismatched";
}

const OUTCOME_BADGE: Record<Outcome["outcome"], { label: string; className: string }> = {
  SUCCESS: {
    label: "Success",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  FAILED: {
    label: "Failed",
    className: "bg-red-500/10 text-red-400 border-red-500/30",
  },
  PENDING: {
    label: "Pending",
    className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
};

function MatchCell({ status }: { status: MatchStatus }) {
  if (status === "matched") {
    return <CheckCircle2Icon className="mx-auto h-4 w-4 text-emerald-400" />;
  }
  if (status === "mismatched") {
    return <XCircleIcon className="mx-auto h-4 w-4 text-red-400" />;
  }
  return <span className="text-xs text-muted-foreground">—</span>;
}

export function OutcomesTableRow({ outcome }: OutcomesTableRowProps) {
  const match = outcomeMatchesPrediction(outcome);
  const badge = OUTCOME_BADGE[outcome.outcome];

  return (
    <TableRow className="border-b border-border/50 transition-colors hover:bg-accent/40">
      <TableCell className="py-3 font-mono text-sm text-muted-foreground">
        {outcome.external_collection_id}
      </TableCell>
      <TableCell className="py-3">
        {outcome.predicted_score !== null &&
        outcome.predicted_score !== undefined &&
        outcome.predicted_risk_level ? (
          <RiskScoreDisplay
            score={outcome.predicted_score}
            riskLevel={outcome.predicted_risk_level}
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
        <MatchCell status={match} />
      </TableCell>
    </TableRow>
  );
}
