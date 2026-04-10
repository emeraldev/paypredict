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
          <TableRow>
            <TableHead className="w-32">Collection ID</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead className="w-48">Risk Score</TableHead>
            <TableHead className="w-36">Method</TableHead>
            <TableHead className="w-32">Amount</TableHead>
            <TableHead className="w-28">Due</TableHead>
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
