import { CalendarIcon, TrendingDownIcon, ZapIcon } from "lucide-react";
import { FactorBreakdown } from "@/components/shared/factor-breakdown";
import { HelpPopover } from "@/components/shared/help-popover";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent } from "@/components/ui/card";
import type { ScoreDetailResponse } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore, getRiskConfig } from "@/lib/utils/format-risk";
import { ReportOutcomeForm } from "./report-outcome-form";

interface RiskDetailContentProps {
  detail: ScoreDetailResponse;
  /** Called after the clerk records an outcome — parent should refetch the
   *  detail so the drawer flips from the form to the recorded outcome view. */
  onOutcomeReported?: () => void;
}

const ACTION_LABELS: Record<string, string> = {
  collect_normally: "Collect normally",
  pre_collection_sms: "Send pre-collection SMS",
  flag_for_review: "Flag for manual review",
  shift_date: "Shift collection date",
};

const SECTION_LABEL = "text-xs font-semibold uppercase tracking-wider text-muted-foreground";

export function RiskDetailContent({
  detail,
  onOutcomeReported,
}: RiskDetailContentProps) {
  const riskConfig = getRiskConfig(detail.risk_level);
  const ctx = detail.customer_context;

  return (
    <div className="space-y-6 p-6">
      {/* Score header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-2">
            <span
              className={cn(
                "text-5xl font-bold tabular-nums tracking-tight",
                riskConfig.color,
              )}
            >
              {displayScore(detail.score)}
            </span>
          </div>
          <RiskBadge level={detail.risk_level} className="text-sm px-3 py-1" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MethodBadge method={detail.collection_method} />
          <span className="font-mono text-xs text-muted-foreground">
            {detail.model_version}
          </span>
        </div>
      </div>

      {/* Recommended action callout */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
        <div className="flex items-center gap-2">
          <ZapIcon className="h-4 w-4 text-amber-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
            Recommended Action
          </span>
          <HelpPopover title="How to act on this">
            <p>
              Each score maps to one of four operational responses. Treat them as
              guidance for your collections workflow — none are enforced by the API.
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
          {ACTION_LABELS[detail.recommended_action] ?? detail.recommended_action}
        </p>
        {detail.recommended_action === "shift_date" &&
          detail.recommended_collection_date &&
          detail.score_improvement != null && (
            <div className="mt-3 space-y-1 border-t border-amber-500/20 pt-3">
              <p className="flex items-center gap-1.5 text-xs text-foreground">
                <CalendarIcon className="h-3.5 w-3.5 text-amber-400" />
                Shift to{" "}
                <span className="font-semibold">
                  {formatDate(detail.recommended_collection_date)}
                </span>
              </p>
              <p className="flex items-center gap-1.5 text-xs text-emerald-400">
                <TrendingDownIcon className="h-3.5 w-3.5" />
                Risk drops by{" "}
                <span className="font-semibold tabular-nums">
                  {Math.round(detail.score_improvement * 100)} pts
                </span>
                {detail.recommended_score != null && (
                  <span className="text-muted-foreground">
                    {" "}
                    (to {displayScore(detail.recommended_score)})
                  </span>
                )}
              </p>
            </div>
          )}
        {detail.recommended_action !== "shift_date" &&
          detail.recommended_collection_date && (
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarIcon className="h-3.5 w-3.5" />
              Suggested date: {formatDate(detail.recommended_collection_date)}
            </p>
          )}
      </div>

      <Separator />

      {/* Collection details */}
      <div className="space-y-2">
        <h3 className={SECTION_LABEL}>Collection</h3>
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-muted-foreground">Customer</span>
          <span className="font-medium text-foreground">{detail.customer_id}</span>
          <span className="text-muted-foreground">Collection ID</span>
          <span className="font-mono text-xs text-foreground">
            {detail.collection_id}
          </span>
          <span className="text-muted-foreground">Amount</span>
          <span className="font-mono font-semibold tabular-nums text-foreground">
            {formatCurrency(detail.collection_amount, detail.collection_currency)}
          </span>
          <span className="text-muted-foreground">Due Date</span>
          <span className="text-foreground">{formatDate(detail.collection_due_date)}</span>
        </div>
      </div>

      <Separator />

      {/* Customer context */}
      <div className="space-y-3">
        <h3 className={SECTION_LABEL}>Customer Context</h3>
        <div className="grid grid-cols-2 gap-3">
          {ctx.total_payments != null && (
            <Card className="border-border/60 bg-muted/40">
              <CardContent className="p-3">
                <p className="text-xs text-muted-foreground">Payment History</p>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {ctx.successful_payments ?? 0}/{ctx.total_payments}
                  {ctx.success_rate != null && ` (${Math.round(ctx.success_rate * 100)}%)`}
                </p>
              </CardContent>
            </Card>
          )}
          {ctx.days_since_last_payment != null && (
            <Card className="border-border/60 bg-muted/40">
              <CardContent className="p-3">
                <p className="text-xs text-muted-foreground">Days Since Last Payment</p>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {ctx.days_since_last_payment}d ago
                </p>
              </CardContent>
            </Card>
          )}
          {detail.instalment_number != null && detail.total_instalments != null && (
            <Card className="border-border/60 bg-muted/40">
              <CardContent className="p-3">
                <p className="text-xs text-muted-foreground">Instalment</p>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {detail.instalment_number} of {detail.total_instalments}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <Separator />

      {/* Factor breakdown */}
      <div className="space-y-3">
        <h3 className={SECTION_LABEL}>Factor Breakdown</h3>
        <FactorBreakdown
          factors={detail.factors}
          skippedFactors={detail.skipped_factors}
        />
      </div>

      <Separator />

      {/* Outcome — either the recorded result, or a form to capture it. */}
      {detail.outcome ? (
        <div className="space-y-2">
          <h3 className={SECTION_LABEL}>Outcome</h3>
          <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
            <div className="flex items-center justify-between">
              <span
                className={cn(
                  "font-semibold",
                  detail.outcome.outcome === "SUCCESS"
                    ? "text-emerald-400"
                    : "text-red-400",
                )}
              >
                {detail.outcome.outcome}
              </span>
              {detail.outcome.attempted_at && (
                <span className="text-xs text-muted-foreground">
                  Attempted {formatDate(detail.outcome.attempted_at)}
                </span>
              )}
            </div>
            {detail.outcome.failure_reason && (
              <p className="mt-1 text-xs text-muted-foreground">
                Reason: {detail.outcome.failure_reason}
              </p>
            )}
          </div>
        </div>
      ) : (
        <ReportOutcomeForm
          scoreId={detail.score_id}
          collectionId={detail.collection_id}
          onReported={() => onOutcomeReported?.()}
        />
      )}
    </div>
  );
}
