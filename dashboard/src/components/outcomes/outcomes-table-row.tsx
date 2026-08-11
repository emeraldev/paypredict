"use client";

import { CheckCircle2Icon, Trash2Icon, XCircleIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { TableCell, TableRow } from "@/components/ui/table";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import { outcomesApi } from "@/lib/api/outcomes";
import type { OutcomeListItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDateTime, formatRelativeTime } from "@/lib/utils/format-date";

interface OutcomesTableRowProps {
  outcome: OutcomeListItem;
  onRemoved?: () => void;
}

const OUTCOME_BADGE: Record<string, { label: string; className: string }> = {
  SUCCESS: {
    label: "Success",
    className: "text-risk-low-fg",
  },
  FAILED: {
    label: "Failed",
    className: "text-risk-high-fg",
  },
};

function MatchCell({ matched }: { matched: boolean | null }) {
  if (matched === true) {
    return <CheckCircle2Icon className="mx-auto h-4 w-4 text-risk-low" />;
  }
  if (matched === false) {
    return <XCircleIcon className="mx-auto h-4 w-4 text-risk-high" />;
  }
  return <span className="text-xs text-muted-foreground">–</span>;
}

export function OutcomesTableRow({ outcome, onRemoved }: OutcomesTableRowProps) {
  const badge = OUTCOME_BADGE[outcome.outcome] ?? OUTCOME_BADGE.FAILED;
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleRemove = async () => {
    try {
      await outcomesApi.remove(outcome.outcome_id);
      toast.success("Outcome removed");
      onRemoved?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove outcome");
      throw err;
    }
  };

  return (
    <TableRow className="border-b border-border/50 transition-colors hover:bg-accent/40">
      <TableCell className="py-3 font-mono text-sm text-muted-foreground">
        {outcome.collection_id}
      </TableCell>
      <TableCell className="py-3">
        {outcome.score !== null && outcome.risk_level ? (
          <RiskScoreDisplay
            score={outcome.score}
            riskLevel={outcome.risk_level}
            showBar={false}
          />
        ) : (
          <span className="text-xs text-muted-foreground">–</span>
        )}
      </TableCell>
      <TableCell className="py-3">
        <span
          className={cn(
            "inline-flex items-center text-sm font-medium",
            badge.className,
          )}
        >
          {badge.label}
        </span>
      </TableCell>
      <TableCell className="py-3 text-sm text-muted-foreground">
        {outcome.failure_reason ?? "–"}
      </TableCell>
      <TableCell className="py-3 text-right font-mono text-sm font-semibold tabular-nums text-foreground">
        {outcome.collection_amount && outcome.collection_currency
          ? formatCurrency(outcome.collection_amount, outcome.collection_currency)
          : "–"}
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
      <TableCell className="py-3 text-right">
        <button
          type="button"
          onClick={() => setConfirmOpen(true)}
          aria-label={`Remove outcome for ${outcome.collection_id}`}
          title="Remove this outcome (use when the entry was wrong)"
          className="rounded p-1 text-muted-foreground/60 transition-colors hover:bg-muted hover:text-risk-high disabled:opacity-50"
        >
          <Trash2Icon className="h-3.5 w-3.5" />
        </button>
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="Remove outcome"
          description={`Remove this ${outcome.outcome.toLowerCase()} outcome for ${outcome.collection_id}? You can record a new one in its place.`}
          confirmLabel="Remove"
          variant="destructive"
          onConfirm={handleRemove}
        />
      </TableCell>
    </TableRow>
  );
}
