"use client";

import { CheckCircle2Icon, FilterXIcon } from "lucide-react";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import type { OutcomeFilter, OutcomeListItem } from "@/lib/api/types";
import { OutcomesTableRow } from "./outcomes-table-row";

interface OutcomesTableProps {
  outcomes: OutcomeListItem[];
  filter?: OutcomeFilter;
  onClearFilter?: () => void;
}

const HEADER_CLS =
  "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

export function OutcomesTable({ outcomes, filter, onClearFilter }: OutcomesTableProps) {
  if (outcomes.length === 0) {
    if (filter && filter !== "ALL") {
      const label =
        filter === "MATCHED" ? "matched predictions" : "mismatched predictions";
      return (
        <EmptyState
          icon={<FilterXIcon className="h-6 w-6" />}
          title={`No ${label} in view`}
          description="Switch to All to see every outcome, or wait for more results to be reported."
          action={
            onClearFilter && (
              <Button variant="outline" size="sm" onClick={onClearFilter}>
                Show all outcomes
              </Button>
            )
          }
        />
      );
    }
    return (
      <EmptyState
        icon={<CheckCircle2Icon className="h-6 w-6" />}
        title="No outcomes reported yet"
        description="Outcomes appear once your lender calls POST /v1/outcomes to report whether a scored collection succeeded or failed."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={HEADER_CLS}>Collection ID</TableHead>
            <TableHead className={HEADER_CLS}>Predicted Risk</TableHead>
            <TableHead className={HEADER_CLS}>Actual Outcome</TableHead>
            <TableHead className={HEADER_CLS}>Failure Reason</TableHead>
            <TableHead className={`${HEADER_CLS} text-right`}>Amount</TableHead>
            <TableHead className={HEADER_CLS}>Attempted</TableHead>
            <TableHead className={HEADER_CLS}>Reported</TableHead>
            <TableHead className={`${HEADER_CLS} text-center`}>Match</TableHead>
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
