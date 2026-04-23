import { CalendarIcon, ZapIcon } from "lucide-react";
import { FactorBreakdown } from "@/components/shared/factor-breakdown";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent } from "@/components/ui/card";
import type { ScoreDetailResponse } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore, getRiskConfig } from "@/lib/utils/format-risk";

interface RiskDetailContentProps {
  detail: ScoreDetailResponse;
}

const ACTION_LABELS: Record<string, string> = {
  collect_normally: "Collect normally",
  pre_collection_sms: "Send pre-collection SMS",
  flag_for_review: "Flag for manual review",
  shift_date: "Shift collection date",
};

const SECTION_LABEL = "text-xs font-semibold uppercase tracking-wider text-muted-foreground";

export function RiskDetailContent({ detail }: RiskDetailContentProps) {
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
        </div>
        <p className="mt-2 text-sm font-medium text-foreground">
          {ACTION_LABELS[detail.recommended_action] ?? detail.recommended_action}
        </p>
        {detail.recommended_collection_date && (
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
          <span className="font-medium text-foreground">{detail.external_customer_id}</span>
          <span className="text-muted-foreground">Collection ID</span>
          <span className="font-mono text-xs text-foreground">
            {detail.external_collection_id}
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
    </div>
  );
}
