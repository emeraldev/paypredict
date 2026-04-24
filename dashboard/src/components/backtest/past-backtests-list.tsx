"use client";

import { CheckCircle2Icon, ClockIcon, XCircleIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { BacktestListItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/utils/format-date";

interface PastBacktestsListProps {
  items: BacktestListItem[];
  onSelect: (id: string) => void;
}

const STATUS_ICON = {
  COMPLETED: <CheckCircle2Icon className="h-4 w-4 text-emerald-400" />,
  PROCESSING: <ClockIcon className="h-4 w-4 text-amber-400" />,
  FAILED: <XCircleIcon className="h-4 w-4 text-red-400" />,
};

export function PastBacktestsList({ items, onSelect }: PastBacktestsListProps) {
  if (items.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Past Backtests</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Name</TableHead>
              <TableHead className="text-right">Collections</TableHead>
              <TableHead className="text-right">Accuracy</TableHead>
              <TableHead className="text-center">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow
                key={item.backtest_id}
                className="cursor-pointer hover:bg-accent/40"
                onClick={() => onSelect(item.backtest_id)}
              >
                <TableCell className="text-sm text-muted-foreground">
                  {formatDateTime(item.created_at)}
                </TableCell>
                <TableCell className="text-sm font-medium">
                  {item.name ?? "Untitled"}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {item.total_collections}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {item.overall_accuracy != null
                    ? `${Math.round(item.overall_accuracy * 100)}%`
                    : "—"}
                </TableCell>
                <TableCell className="text-center">
                  {STATUS_ICON[item.status as keyof typeof STATUS_ICON] ??
                    STATUS_ICON.PROCESSING}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
