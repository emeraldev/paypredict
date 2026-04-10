"use client";

import { InboxIcon } from "lucide-react";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import type { Outcome } from "@/lib/api/types";
import { OutcomesTableRow } from "./outcomes-table-row";

interface OutcomesTableProps {
  outcomes: Outcome[];
}

const HEADER_CLS =
  "text-xs font-semibold uppercase tracking-wider text-muted-foreground";

export function OutcomesTable({ outcomes }: OutcomesTableProps) {
  if (outcomes.length === 0) {
    return (
      <EmptyState
        icon={<InboxIcon className="h-10 w-10" />}
        title="No outcomes found"
        description="Try changing the filter tab."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={`${HEADER_CLS} w-12`} />
            <TableHead className={`${HEADER_CLS} w-32`}>Collection ID</TableHead>
            <TableHead className={`${HEADER_CLS} w-36`}>Predicted</TableHead>
            <TableHead className={`${HEADER_CLS} w-24 text-center`}>Actual</TableHead>
            <TableHead className={`${HEADER_CLS} w-32`}>Match</TableHead>
            <TableHead className={`${HEADER_CLS} w-36 text-center`}>Method</TableHead>
            <TableHead className={`${HEADER_CLS} w-32 text-right`}>Amount</TableHead>
            <TableHead className={HEADER_CLS}>Attempted</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {outcomes.map((outcome, index) => (
            <OutcomesTableRow
              key={outcome.outcome_id}
              outcome={outcome}
              index={index}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
