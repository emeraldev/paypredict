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
import type { Collection } from "@/lib/api/types";
import { CollectionsTableRow } from "./collections-table-row";

interface CollectionsTableProps {
  collections: Collection[];
  onRowClick: (collection: Collection) => void;
}

const HEADER_CLS =
  "text-xs font-semibold uppercase tracking-wider text-muted-foreground";

export function CollectionsTable({ collections, onRowClick }: CollectionsTableProps) {
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
            <TableHead className={`${HEADER_CLS} w-32`}>Collection ID</TableHead>
            <TableHead className={HEADER_CLS}>Customer</TableHead>
            <TableHead className={`${HEADER_CLS} w-[160px]`}>Risk Score</TableHead>
            <TableHead className={`${HEADER_CLS} w-36`}>Method</TableHead>
            <TableHead className={`${HEADER_CLS} w-32 text-right`}>Amount</TableHead>
            <TableHead className={`${HEADER_CLS} w-32`}>Due</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {collections.map((collection, index) => (
            <CollectionsTableRow
              key={collection.score_id}
              collection={collection}
              index={index}
              onClick={() => onRowClick(collection)}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
