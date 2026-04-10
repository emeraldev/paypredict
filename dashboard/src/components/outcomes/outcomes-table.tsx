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
          <TableRow>
            <TableHead className="w-12" />
            <TableHead className="w-32">Collection ID</TableHead>
            <TableHead className="w-36">Predicted</TableHead>
            <TableHead className="w-24">Actual</TableHead>
            <TableHead className="w-32">Match</TableHead>
            <TableHead className="w-36">Method</TableHead>
            <TableHead className="w-32">Amount</TableHead>
            <TableHead>Attempted</TableHead>
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
