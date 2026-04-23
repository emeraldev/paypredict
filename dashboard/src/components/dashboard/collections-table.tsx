"use client";

import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon, InboxIcon } from "lucide-react";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import type { ScoreListItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { CollectionsTableRow } from "./collections-table-row";

export type CollectionsSortField = "score" | "due_date";
export type SortDirection = "asc" | "desc";

interface CollectionsTableProps {
  collections: ScoreListItem[];
  onRowClick: (collection: ScoreListItem) => void;
  sortField: CollectionsSortField;
  sortDirection: SortDirection;
  onSortChange: (field: CollectionsSortField) => void;
}

const HEADER_CLS =
  "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

interface SortableHeaderProps {
  label: string;
  field: CollectionsSortField;
  active: boolean;
  direction: SortDirection;
  onClick: () => void;
}

function SortableHeader({ label, active, direction, onClick }: SortableHeaderProps) {
  const Icon = !active ? ArrowUpDownIcon : direction === "asc" ? ArrowUpIcon : ArrowDownIcon;
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1 transition-colors hover:text-foreground"
    >
      {label}
      <Icon className="h-3 w-3" />
    </button>
  );
}

export function CollectionsTable({
  collections,
  onRowClick,
  sortField,
  sortDirection,
  onSortChange,
}: CollectionsTableProps) {
  if (collections.length === 0) {
    return (
      <EmptyState
        icon={<InboxIcon className="h-10 w-10" />}
        title="No collections found"
        description="Try adjusting your filters or search query."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={cn(HEADER_CLS, "w-[150px]")}>
              <SortableHeader
                label="Risk"
                field="score"
                active={sortField === "score"}
                direction={sortDirection}
                onClick={() => onSortChange("score")}
              />
            </TableHead>
            <TableHead className={HEADER_CLS}>Customer</TableHead>
            <TableHead className={cn(HEADER_CLS, "w-[120px] text-right")}>Amount</TableHead>
            <TableHead className={cn(HEADER_CLS, "w-[160px]")}>
              <SortableHeader
                label="Due Date"
                field="due_date"
                active={sortField === "due_date"}
                direction={sortDirection}
                onClick={() => onSortChange("due_date")}
              />
            </TableHead>
            <TableHead className={cn(HEADER_CLS, "w-[120px]")}>Instalment</TableHead>
            <TableHead className={cn(HEADER_CLS, "w-[140px]")}>Method</TableHead>
            <TableHead className={cn(HEADER_CLS, "w-[80px] text-right")} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {collections.map((collection) => (
            <CollectionsTableRow
              key={collection.score_id}
              collection={collection}
              onClick={() => onRowClick(collection)}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
