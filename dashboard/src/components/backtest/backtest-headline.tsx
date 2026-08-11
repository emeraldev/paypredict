import { Card, CardContent } from "@/components/ui/card";
import type { BacktestSummary } from "@/lib/api/types";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

interface BacktestHeadlineProps {
  summary: BacktestSummary;
}

export function BacktestHeadline({ summary }: BacktestHeadlineProps) {
  return (
    <Card className="border-risk-low/30 bg-risk-low-bg">
      <CardContent className="p-6 text-center">
        <p className="text-sm font-medium text-risk-low-fg">
          Backtest Result
        </p>
        <p className="mt-2 text-3xl font-semibold text-risk-low-fg">
          We would have predicted{" "}
          <span className="text-4xl">{Math.round(summary.overall_accuracy * 100)}%</span>{" "}
          of your failures in advance
        </p>
        <p className="mt-2 text-lg text-risk-low-fg">
          Estimated recovery:{" "}
          <span className="font-semibold">
            {formatCompactCurrency(summary.estimated_annual_recovery, "ZAR")}
          </span>
          {summary.estimated_annual_recovery > summary.flagged_in_advance_value && " annually"}
        </p>
      </CardContent>
    </Card>
  );
}
