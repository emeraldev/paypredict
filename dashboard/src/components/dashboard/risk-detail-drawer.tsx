"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { Collection } from "@/lib/api/types";
import { RiskDetailContent } from "./risk-detail-content";

interface RiskDetailDrawerProps {
  collection: Collection | null;
  open: boolean;
  onClose: () => void;
}

export function RiskDetailDrawer({ collection, open, onClose }: RiskDetailDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full max-w-xl overflow-y-auto sm:max-w-xl">
        <SheetHeader className="border-b border-border pb-4">
          <SheetTitle>Collection Detail</SheetTitle>
          <SheetDescription>
            {collection?.external_collection_id ?? "Loading..."}
          </SheetDescription>
        </SheetHeader>
        <div className="px-6 pb-6 pt-4">
          {collection && <RiskDetailContent collection={collection} />}
        </div>
      </SheetContent>
    </Sheet>
  );
}
