"use client";

import { CheckCircle2Icon, ClockIcon, XCircleIcon } from "lucide-react";
import type { CustomerJourneyEntry } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore, getRiskConfig } from "@/lib/utils/format-risk";

interface CustomerJourneySectionProps {
  entries: CustomerJourneyEntry[];
}

const SECTION_LABEL = "text-xs font-semibold uppercase tracking-wider text-muted-foreground";

/**
 * Chronological loan timeline for the drawer. Renders one row per
 * scored collection for the same customer, with the current row
 * highlighted so a demo user (or a real lender) sees the full
 * customer journey at a glance instead of a single standalone
 * collection.
 *
 * Renders nothing when there's zero or one entry — a singleton
 * customer has no timeline worth showing.
 */
export function CustomerJourneySection({ entries }: CustomerJourneySectionProps) {
  if (entries.length <= 1) {
    // Zero (impossible in practice — current row is always present)
    // or one (singleton customer — no journey to render).
    return null;
  }

  return (
    <div className="space-y-3">
      <h3 className={SECTION_LABEL}>Customer Journey</h3>
      <div className="rounded-md border border-border bg-muted/30">
        <ol className="divide-y divide-border">
          {entries.map((entry, i) => (
            <JourneyRow key={entry.score_id} entry={entry} index={i} total={entries.length} />
          ))}
        </ol>
      </div>
    </div>
  );
}

function JourneyRow({
  entry,
  index,
  total,
}: {
  entry: CustomerJourneyEntry;
  index: number;
  total: number;
}) {
  const risk = getRiskConfig(entry.risk_level);
  const positionLabel =
    entry.instalment_number != null && entry.total_instalments != null
      ? `${entry.instalment_number}/${entry.total_instalments}`
      : `#${index + 1}`;

  return (
    <li
      className={cn(
        "flex items-start gap-3 px-3 py-2.5",
        entry.is_current && "bg-primary/5",
      )}
    >
      {/* Timeline dot column */}
      <div className="mt-1 flex flex-col items-center">
        <span
          className={cn(
            "flex h-2.5 w-2.5 shrink-0 rounded-full",
            entry.is_current ? "bg-primary ring-2 ring-primary/30" : "bg-muted-foreground/40",
          )}
        />
        {index < total - 1 && (
          <span className="mt-1 h-full w-px bg-border" aria-hidden />
        )}
      </div>

      {/* Body */}
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-medium text-foreground">
            Instalment {positionLabel}
          </span>
          <span
            className="text-xs text-muted-foreground"
            title={new Date(entry.scored_at).toLocaleString()}
          >
            {formatDate(entry.collection_due_date)}
          </span>
        </div>

        <div className="mt-0.5 flex items-center gap-2 text-xs">
          <span className={cn("font-mono font-semibold tabular-nums", risk.color)}>
            {displayScore(entry.score)}
          </span>
          <span className="text-muted-foreground">·</span>
          <span className="text-muted-foreground">
            {formatCurrency(entry.collection_amount, entry.collection_currency)}
          </span>
          <span className="text-muted-foreground">·</span>
          <OutcomePill outcome={entry.outcome} />
          {entry.is_current && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                You are here
              </span>
            </>
          )}
        </div>
      </div>
    </li>
  );
}

function OutcomePill({ outcome }: { outcome: string | null }) {
  if (outcome === "SUCCESS") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-risk-low-fg">
        <CheckCircle2Icon className="h-3 w-3" />
        Success
      </span>
    );
  }
  if (outcome === "FAILED") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-risk-high-fg">
        <XCircleIcon className="h-3 w-3" />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <ClockIcon className="h-3 w-3" />
      Pending
    </span>
  );
}
