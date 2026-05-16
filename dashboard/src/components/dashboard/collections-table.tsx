"use client";

import {
  ArrowDownIcon,
  ArrowUpDownIcon,
  ArrowUpIcon,
  FilterXIcon,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import type { ScoreListItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { CollectionsOnboarding } from "./collections-onboarding";
import { CollectionsTableRow } from "./collections-table-row";

export type CollectionsSortField = "score" | "due_date" | "customer" | "amount" | "method";
export type SortDirection = "asc" | "desc";

interface CollectionsTableProps {
  collections: ScoreListItem[];
  onRowClick: (collection: ScoreListItem) => void;
  sortField: CollectionsSortField;
  sortDirection: SortDirection;
  onSortChange: (field: CollectionsSortField) => void;
  hasActiveFilters?: boolean;
  onClearFilters?: () => void;
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

function SortableHeader({
  label,
  active,
  direction,
  onClick,
  align = "left",
}: SortableHeaderProps & { align?: "left" | "right" }) {
  const Icon = !active ? ArrowUpDownIcon : direction === "asc" ? ArrowUpIcon : ArrowDownIcon;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-1 transition-colors hover:text-foreground",
        align === "right" && "justify-end",
      )}
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
  hasActiveFilters = false,
  onClearFilters,
}: CollectionsTableProps) {
  if (collections.length === 0) {
    return hasActiveFilters ? (
      <EmptyState
        icon={<FilterXIcon className="h-6 w-6" />}
        title="No collections match these filters"
        description="Try widening the date range, clearing the search, or removing the method filter."
        action={
          onClearFilters && (
            <Button variant="outline" size="sm" onClick={onClearFilters}>
              Clear filters
            </Button>
          )
        }
      />
    ) : (
      <CollectionsOnboarding />
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={HEADER_CLS}>
              <SortableHeader
                label="Risk"
                field="score"
                active={sortField === "score"}
                direction={sortDirection}
                onClick={() => onSortChange("score")}
              />
            </TableHead>
            <TableHead className={HEADER_CLS}>
              <SortableHeader
                label="Customer"
                field="customer"
                active={sortField === "customer"}
                direction={sortDirection}
                onClick={() => onSortChange("customer")}
              />
            </TableHead>
            <TableHead className={cn(HEADER_CLS, "text-right")}>
              <SortableHeader
                label="Amount"
                field="amount"
                active={sortField === "amount"}
                direction={sortDirection}
                onClick={() => onSortChange("amount")}
                align="right"
              />
            </TableHead>
            <TableHead className={HEADER_CLS}>
              <SortableHeader
                label="Due Date"
                field="due_date"
                active={sortField === "due_date"}
                direction={sortDirection}
                onClick={() => onSortChange("due_date")}
              />
            </TableHead>
            <TableHead className={HEADER_CLS}>Instalment</TableHead>
            <TableHead className={HEADER_CLS}>
              <SortableHeader
                label="Method"
                field="method"
                active={sortField === "method"}
                direction={sortDirection}
                onClick={() => onSortChange("method")}
              />
            </TableHead>
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
