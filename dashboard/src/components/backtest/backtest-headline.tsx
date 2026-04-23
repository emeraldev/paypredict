import { Card, CardContent } from "@/components/ui/card";
import type { BacktestSummary } from "@/lib/api/types";
import { formatCompactCurrency } from "@/lib/utils/format-currency";

interface BacktestHeadlineProps {
  summary: BacktestSummary;
}

export function BacktestHeadline({ summary }: BacktestHeadlineProps) {
  return (
    <Card className="bg-emerald-50 dark:bg-emerald-950/30 border-emerald-500/30">
      <CardContent className="p-6 text-center">
        <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
          Backtest Result
        </p>
        <p className="mt-2 text-3xl font-bold text-emerald-800 dark:text-emerald-300">
          We would have predicted{" "}
          <span className="text-4xl">{Math.round(summary.overall_accuracy * 100)}%</span>{" "}
          of your failures in advance
        </p>
        <p className="mt-2 text-lg text-emerald-700 dark:text-emerald-400">
          Recovering an estimated{" "}
          <span className="font-bold">
            {formatCompactCurrency(summary.estimated_annual_recovery, "ZAR")}
          </span>{" "}
          annually
        </p>
      </CardContent>
    </Card>
  );
}
