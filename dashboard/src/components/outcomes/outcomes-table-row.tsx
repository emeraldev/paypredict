"use client";

import { CheckCircleIcon, CheckIcon, ClockIcon, XCircleIcon, XIcon } from "lucide-react";
import { TableCell, TableRow } from "@/components/ui/table";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { Outcome } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatRelativeTime } from "@/lib/utils/format-date";

interface OutcomesTableRowProps {
  outcome: Outcome;
  index: number;
}

type MatchStatus = "matched" | "mismatched" | "pending";

function outcomeMatchesPrediction(outcome: Outcome): MatchStatus {
  if (outcome.outcome === "PENDING") return "pending";
  if (!outcome.predicted_risk_level) return "pending";
  const predictedFailure = outcome.predicted_risk_level === "HIGH";
  const actuallyFailed = outcome.outcome === "FAILED";
  return predictedFailure === actuallyFailed ? "matched" : "mismatched";
}

function OutcomeIcon({ outcome }: { outcome: Outcome["outcome"] }) {
  if (outcome === "SUCCESS") {
    return (
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400">
        <CheckIcon className="h-4 w-4" />
      </span>
    );
  }
  if (outcome === "FAILED") {
    return (
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-red-500/10 text-red-400">
        <XIcon className="h-4 w-4" />
      </span>
    );
  }
  return (
    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-500/10 text-amber-400">
      <ClockIcon className="h-4 w-4" />
    </span>
  );
}

function MatchIndicator({ status }: { status: MatchStatus }) {
  if (status === "matched") {
    return (
      <div className="flex items-center gap-1.5 text-emerald-400">
        <CheckCircleIcon className="h-4 w-4" />
        <span className="text-xs font-medium">Matched</span>
      </div>
    );
  }
  if (status === "mismatched") {
    return (
      <div className="flex items-center gap-1.5 text-red-400">
        <XCircleIcon className="h-4 w-4" />
        <span className="text-xs font-medium">Missed</span>
      </div>
    );
  }
  return <span className="text-xs text-muted-foreground">—</span>;
}

const OUTCOME_BADGE: Record<Outcome["outcome"], string> = {
  SUCCESS: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
  FAILED: "bg-red-500/10 text-red-400 border border-red-500/30",
  PENDING: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
};

export function OutcomesTableRow({ outcome, index }: OutcomesTableRowProps) {
  const match = outcomeMatchesPrediction(outcome);

  return (
    <TableRow
      className={cn(
        "transition-colors",
        index % 2 === 0 ? "bg-transparent" : "bg-muted/30",
      )}
    >
      <TableCell>
        <OutcomeIcon outcome={outcome.outcome} />
      </TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">
        {outcome.external_collection_id}
      </TableCell>
      <TableCell>
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
      <TableCell className="text-center">
        <span
          className={cn(
            "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
            OUTCOME_BADGE[outcome.outcome],
          )}
        >
          {outcome.outcome}
        </span>
      </TableCell>
      <TableCell>
        <MatchIndicator status={match} />
      </TableCell>
      <TableCell className="text-center">
        {outcome.collection_method ? (
          <MethodBadge method={outcome.collection_method} />
        ) : null}
      </TableCell>
      <TableCell className="text-right font-mono text-sm font-semibold tabular-nums text-foreground">
        {outcome.collection_amount && outcome.collection_currency
          ? formatCurrency(outcome.collection_amount, outcome.collection_currency)
          : "—"}
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">
        {formatRelativeTime(outcome.attempted_at)}
      </TableCell>
    </TableRow>
  );
}
