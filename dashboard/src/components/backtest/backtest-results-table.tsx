"use client";

import { CheckCircle2Icon, InboxIcon, XCircleIcon } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import { RiskScoreDisplay } from "@/components/shared/risk-score-display";
import type { BacktestResponse } from "@/lib/api/types";
import type { RiskLevel } from "@/lib/utils/format-risk";

interface BacktestResultsTableProps {
  backtest: BacktestResponse;
}

export function BacktestResultsTable({ backtest }: BacktestResultsTableProps) {
  // The full results endpoint doesn't return individual items in the
  // current response shape — the table shows aggregated data from the
  // confusion matrix and risk distribution. For a detailed drilldown,
  // we'd need a separate endpoint. For now, show the risk buckets as rows.
  const dist = backtest.risk_distribution;
  if (!dist) {
    return (
      <EmptyState
        icon={<InboxIcon className="h-10 w-10" />}
        title="No results"
        description="Run a backtest to see results."
      />
    );
  }

  const rows = [
    { level: "HIGH" as RiskLevel, ...dist.high },
    { level: "MEDIUM" as RiskLevel, ...dist.medium },
    { level: "LOW" as RiskLevel, ...dist.low },
  ];

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Risk Level</TableHead>
          <TableHead className="text-right">Count</TableHead>
          <TableHead className="text-right">Actually Failed</TableHead>
          <TableHead className="text-right">Accuracy</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.level}>
            <TableCell>
              <RiskScoreDisplay
                score={row.level === "HIGH" ? 0.8 : row.level === "MEDIUM" ? 0.45 : 0.15}
                riskLevel={row.level}
                showBar={false}
              />
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {row.count}
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {row.actually_failed}
            </TableCell>
            <TableCell className="text-right">
              <span className="inline-flex items-center gap-1.5">
                {row.accuracy >= 0.7 ? (
                  <CheckCircle2Icon className="h-4 w-4 text-emerald-400" />
                ) : (
                  <XCircleIcon className="h-4 w-4 text-amber-400" />
                )}
                <span className="font-mono tabular-nums">
                  {Math.round(row.accuracy * 100)}%
                </span>
              </span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
