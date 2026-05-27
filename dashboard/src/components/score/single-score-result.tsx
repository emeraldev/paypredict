"use client";

import { CalendarIcon, TrendingDownIcon, ZapIcon } from "lucide-react";
import { FactorBreakdown } from "@/components/shared/factor-breakdown";
import { HelpPopover } from "@/components/shared/help-popover";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ScoreResponse } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore, getRiskConfig } from "@/lib/utils/format-risk";

const ACTION_LABELS: Record<string, string> = {
  collect_normally: "Collect normally",
  pre_collection_sms: "Send pre-collection SMS",
  flag_for_review: "Flag for manual review",
  shift_date: "Shift collection date",
};

interface SingleScoreResultProps {
  result: ScoreResponse;
  onReset: () => void;
}

export function SingleScoreResult({ result, onReset }: SingleScoreResultProps) {
  const riskConfig = getRiskConfig(result.risk_level);
  return (
    <Card>
      <CardContent className="space-y-6 p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-3">
            <span
              className={cn(
                "text-5xl font-bold tabular-nums tracking-tight",
                riskConfig.color,
              )}
            >
              {displayScore(result.score)}
            </span>
            <RiskBadge level={result.risk_level} className="text-sm px-3 py-1" />
          </div>
          <button
            onClick={onReset}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Score another
          </button>
        </div>

        {/* Recommended action */}
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
          <div className="flex items-center gap-2">
            <ZapIcon className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Recommended Action
            </span>
            <HelpPopover title="How to act on this">
              <p>
                Four possible actions. None are enforced — they&apos;re guidance
                for your collections workflow.
              </p>
              <ul className="space-y-1.5">
                <li>
                  <span className="font-medium text-foreground">Collect normally</span>
                  {" "}— attempt as planned.
                </li>
                <li>
                  <span className="font-medium text-foreground">Send pre-collection SMS</span>
                  {" "}— nudge the customer before charging.
                </li>
                <li>
                  <span className="font-medium text-foreground">Flag for manual review</span>
                  {" "}— pause and have a human decide.
                </li>
                <li>
                  <span className="font-medium text-foreground">Shift collection date</span>
                  {" "}— retry on the suggested date for better odds.
                </li>
              </ul>
            </HelpPopover>
          </div>
          <p className="mt-2 text-sm font-medium text-foreground">
            {ACTION_LABELS[result.recommended_action] ?? result.recommended_action}
          </p>
          {result.recommended_action === "shift_date" &&
            result.recommended_collection_date &&
            result.score_improvement != null && (
              <div className="mt-3 space-y-1 border-t border-amber-500/20 pt-3">
                <p className="flex items-center gap-1.5 text-xs text-foreground">
                  <CalendarIcon className="h-3.5 w-3.5 text-amber-400" />
                  Shift to{" "}
                  <span className="font-semibold">
                    {formatDate(result.recommended_collection_date)}
                  </span>
                </p>
                <p className="flex items-center gap-1.5 text-xs text-emerald-400">
                  <TrendingDownIcon className="h-3.5 w-3.5" />
                  Risk drops by{" "}
                  <span className="font-semibold tabular-nums">
                    {Math.round(result.score_improvement * 100)} pts
                  </span>
                </p>
              </div>
            )}
        </div>

        <Separator />

        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Why this score
          </h3>
          <FactorBreakdown
            factors={result.factors}
            skippedFactors={result.skipped_factors}
          />
        </div>
      </CardContent>
    </Card>
  );
}
