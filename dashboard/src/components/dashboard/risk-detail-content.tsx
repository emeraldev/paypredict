import { CalendarIcon, ZapIcon } from "lucide-react";
import { CustomerContextCards } from "@/components/shared/customer-context-cards";
import { FactorBreakdown } from "@/components/shared/factor-breakdown";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Separator } from "@/components/ui/separator";
import type { Collection } from "@/lib/api/types";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore } from "@/lib/utils/format-risk";

interface RiskDetailContentProps {
  collection: Collection;
}

const ACTION_LABELS: Record<string, string> = {
  collect_normally: "Collect normally",
  pre_collection_sms: "Send pre-collection SMS",
  flag_for_review: "Flag for manual review",
  shift_date: "Shift collection date",
};

export function RiskDetailContent({ collection }: RiskDetailContentProps) {
  return (
    <div className="space-y-6">
      {/* Score header */}
      <div className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <div>
            <p className="text-xs text-muted-foreground">Risk Score</p>
            <p className="text-4xl font-semibold tracking-tight tabular-nums">
              {displayScore(collection.score)}
              <span className="ml-1 text-base font-normal text-muted-foreground">/100</span>
            </p>
          </div>
          <RiskBadge level={collection.risk_level} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MethodBadge method={collection.collection_method} />
          <span className="text-xs text-muted-foreground">
            {collection.model_version}
          </span>
        </div>
      </div>

      {/* Recommended action callout */}
      <div className="rounded-lg border border-border bg-muted/40 p-4">
        <div className="flex items-start gap-3">
          <ZapIcon className="mt-0.5 h-4 w-4 text-amber-400 shrink-0" />
          <div className="flex-1 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Recommended Action
            </p>
            <p className="text-sm font-medium text-foreground">
              {ACTION_LABELS[collection.recommended_action] ?? collection.recommended_action}
            </p>
            {collection.recommended_collection_date && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                <CalendarIcon className="h-3 w-3" />
                <span>
                  Suggested date: {formatDate(collection.recommended_collection_date)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <Separator />

      {/* Collection details */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Collection</h3>
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-muted-foreground">Customer</span>
          <span className="font-medium">{collection.external_customer_id}</span>
          <span className="text-muted-foreground">Collection ID</span>
          <span className="font-mono text-xs">{collection.external_collection_id}</span>
          <span className="text-muted-foreground">Amount</span>
          <span className="font-mono tabular-nums">
            {formatCurrency(collection.collection_amount, collection.collection_currency)}
          </span>
          <span className="text-muted-foreground">Due Date</span>
          <span>{formatDate(collection.collection_due_date)}</span>
        </div>
      </div>

      <Separator />

      {/* Customer context */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Customer Context</h3>
        <CustomerContextCards customer={collection.customer_data} />
      </div>

      <Separator />

      {/* Factor breakdown */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Factor Breakdown</h3>
        <FactorBreakdown
          factors={collection.factors}
          skippedFactors={collection.skipped_factors}
        />
      </div>
    </div>
  );
}
