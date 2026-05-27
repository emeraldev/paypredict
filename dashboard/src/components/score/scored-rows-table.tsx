"use client";

import { DownloadIcon } from "lucide-react";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCurrency } from "@/lib/utils/format-currency";
import { formatDate } from "@/lib/utils/format-date";
import { displayScore, type RiskLevel } from "@/lib/utils/format-risk";
import type {
  CollectionMethod,
} from "@/lib/utils/format-method";
import type { Currency } from "@/lib/utils/format-currency";
import type { ScoredUploadRow } from "@/lib/api/scores";

interface ScoredRowsTableProps {
  rows: ScoredUploadRow[];
}

// Order most-actionable first: highest score (=highest risk) at the top.
function sortHighestRiskFirst(rows: ScoredUploadRow[]): ScoredUploadRow[] {
  return [...rows].sort((a, b) => b.score - a.score);
}

const CSV_COLUMNS: (keyof ScoredUploadRow | "score_pct")[] = [
  "customer_id",
  "collection_id",
  "collection_amount",
  "collection_currency",
  "collection_due_date",
  "collection_method",
  "score_pct",
  "risk_level",
  "recommended_action",
  "recommended_collection_date",
  "score_id",
];

function rowsToCsv(rows: ScoredUploadRow[]): string {
  const header = CSV_COLUMNS.join(",");
  const body = rows.map((row) =>
    CSV_COLUMNS.map((col) => {
      if (col === "score_pct") return displayScore(row.score);
      const v = row[col];
      if (v === null || v === undefined) return "";
      const s = String(v);
      // Quote any value that contains a comma, quote, or newline
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(","),
  );
  return [header, ...body].join("\n") + "\n";
}

function downloadCsv(rows: ScoredUploadRow[]): void {
  const csv = rowsToCsv(sortHighestRiskFirst(rows));
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const today = new Date().toISOString().slice(0, 10);
  const a = document.createElement("a");
  a.href = url;
  a.download = `paypredict_scored_${today}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function ScoredRowsTable({ rows }: ScoredRowsTableProps) {
  const sorted = sortHighestRiskFirst(rows);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div>
          <CardTitle className="text-base">Scored rows</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Sorted highest risk first. These rows are also live on the main dashboard.
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={() => downloadCsv(rows)}>
          <DownloadIcon className="mr-1.5 h-3.5 w-3.5" />
          Download as CSV
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Risk</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Collection</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Due</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((row) => (
                <TableRow key={row.score_id}>
                  <TableCell>
                    <RiskBadge level={row.risk_level as RiskLevel} />
                  </TableCell>
                  <TableCell className="font-mono tabular-nums font-medium">
                    {displayScore(row.score)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{row.customer_id}</TableCell>
                  <TableCell className="font-mono text-xs">{row.collection_id}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatCurrency(row.collection_amount, row.collection_currency as Currency)}
                  </TableCell>
                  <TableCell>{formatDate(row.collection_due_date)}</TableCell>
                  <TableCell>
                    <MethodBadge method={row.collection_method as CollectionMethod} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {row.recommended_action.replace(/_/g, " ")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
