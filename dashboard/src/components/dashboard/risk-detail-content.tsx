import { CalendarIcon, ZapIcon } from "lucide-react";
import { CustomerContextCards } from "@/components/shared/customer-context-cards";
import { FactorBreakdown } from "@/components/shared/factor-breakdown";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Separator } from "@/components/ui/separator";
import type { Collection } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore, getRiskConfig } from "@/lib/utils/format-risk";

interface RiskDetailContentProps {
  collection: Collection;
}

const ACTION_LABELS: Record<string, string> = {
  collect_normally: "Collect normally",
  pre_collection_sms: "Send pre-collection SMS",
  flag_for_review: "Flag for manual review",
  shift_date: "Shift collection date",
};

const SECTION_LABEL = "text-xs font-semibold uppercase tracking-wider text-muted-foreground";

export function RiskDetailContent({ collection }: RiskDetailContentProps) {
  const riskConfig = getRiskConfig(collection.risk_level);

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
              {displayScore(collection.score)}
            </span>
          </div>
          <RiskBadge level={collection.risk_level} className="text-sm px-3 py-1" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MethodBadge method={collection.collection_method} />
          <span className="font-mono text-xs text-muted-foreground">
            {collection.model_version}
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
          {ACTION_LABELS[collection.recommended_action] ?? collection.recommended_action}
        </p>
        {collection.recommended_collection_date && (
          <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <CalendarIcon className="h-3.5 w-3.5" />
            Suggested date: {formatDate(collection.recommended_collection_date)}
          </p>
        )}
      </div>

      <Separator />

      {/* Collection details */}
      <div className="space-y-2">
        <h3 className={SECTION_LABEL}>Collection</h3>
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-muted-foreground">Customer</span>
          <span className="font-medium text-foreground">{collection.external_customer_id}</span>
          <span className="text-muted-foreground">Collection ID</span>
          <span className="font-mono text-xs text-foreground">
            {collection.external_collection_id}
          </span>
          <span className="text-muted-foreground">Amount</span>
          <span className="font-mono font-semibold tabular-nums text-foreground">
            {formatCurrency(collection.collection_amount, collection.collection_currency)}
          </span>
          <span className="text-muted-foreground">Due Date</span>
          <span className="text-foreground">{formatDate(collection.collection_due_date)}</span>
        </div>
      </div>

      <Separator />

      {/* Customer context */}
      <div className="space-y-3">
        <h3 className={SECTION_LABEL}>Customer Context</h3>
        <CustomerContextCards customer={collection.customer_data} />
      </div>

      <Separator />

      {/* Factor breakdown */}
      <div className="space-y-3">
        <h3 className={SECTION_LABEL}>Factor Breakdown</h3>
        <FactorBreakdown
          factors={collection.factors}
          skippedFactors={collection.skipped_factors}
        />
      </div>
    </div>
  );
}
