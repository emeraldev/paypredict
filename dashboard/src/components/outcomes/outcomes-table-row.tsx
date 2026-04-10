"use client";

import { CheckIcon, ClockIcon, XIcon } from "lucide-react";
import { TableCell, TableRow } from "@/components/ui/table";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { Outcome } from "@/lib/api/types";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatRelativeTime } from "@/lib/utils/format-date";
import { cn } from "@/lib/utils";

interface OutcomesTableRowProps {
  outcome: Outcome;
}

function outcomeMatchesPrediction(outcome: Outcome): "matched" | "mismatched" | "pending" {
  if (outcome.outcome === "PENDING") return "pending";
  if (!outcome.predicted_risk_level) return "pending";
  const predictedFailure = outcome.predicted_risk_level === "HIGH";
  const actuallyFailed = outcome.outcome === "FAILED";
  return predictedFailure === actuallyFailed ? "matched" : "mismatched";
}

function OutcomeIcon({ outcome }: { outcome: Outcome["outcome"] }) {
  if (outcome === "SUCCESS") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-950 text-emerald-400">
        <CheckIcon className="h-3.5 w-3.5" />
      </span>
    );
  }
  if (outcome === "FAILED") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-red-950 text-red-400">
        <XIcon className="h-3.5 w-3.5" />
      </span>
    );
  }
  return (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-amber-950 text-amber-400">
      <ClockIcon className="h-3.5 w-3.5" />
    </span>
  );
}

export function OutcomesTableRow({ outcome }: OutcomesTableRowProps) {
  const match = outcomeMatchesPrediction(outcome);

  return (
    <TableRow>
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
      <TableCell>
        <span
          className={cn(
            "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
            outcome.outcome === "SUCCESS" && "bg-emerald-950 text-emerald-400",
            outcome.outcome === "FAILED" && "bg-red-950 text-red-400",
            outcome.outcome === "PENDING" && "bg-amber-950 text-amber-400",
          )}
        >
          {outcome.outcome}
        </span>
      </TableCell>
      <TableCell>
        {match === "matched" && (
          <span className="text-xs text-emerald-400">✓ Matched</span>
        )}
        {match === "mismatched" && (
          <span className="text-xs text-red-400">✗ Mismatched</span>
        )}
        {match === "pending" && (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell>
        {outcome.collection_method ? <MethodBadge method={outcome.collection_method} /> : null}
      </TableCell>
      <TableCell className="font-mono tabular-nums">
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
