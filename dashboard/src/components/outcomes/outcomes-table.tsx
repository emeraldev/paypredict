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
import type { OutcomeListItem } from "@/lib/api/types";
import { OutcomesTableRow } from "./outcomes-table-row";

interface OutcomesTableProps {
  outcomes: OutcomeListItem[];
}

const HEADER_CLS =
  "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

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
            <TableHead className={`${HEADER_CLS} w-[140px]`}>Collection ID</TableHead>
            <TableHead className={`${HEADER_CLS} w-[150px]`}>Predicted Risk</TableHead>
            <TableHead className={`${HEADER_CLS} w-[130px]`}>Actual Outcome</TableHead>
            <TableHead className={HEADER_CLS}>Failure Reason</TableHead>
            <TableHead className={`${HEADER_CLS} w-[120px] text-right`}>Amount</TableHead>
            <TableHead className={`${HEADER_CLS} w-[140px]`}>Attempted</TableHead>
            <TableHead className={`${HEADER_CLS} w-[120px]`}>Reported</TableHead>
            <TableHead className={`${HEADER_CLS} w-[60px] text-center`}>Match</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {outcomes.map((outcome) => (
            <OutcomesTableRow key={outcome.outcome_id} outcome={outcome} />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
