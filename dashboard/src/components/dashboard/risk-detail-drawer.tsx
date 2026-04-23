"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { ScoreDetailResponse } from "@/lib/api/types";
import { RiskDetailContent } from "./risk-detail-content";

interface RiskDetailDrawerProps {
  detail: ScoreDetailResponse | null;
  open: boolean;
  onClose: () => void;
}

export function RiskDetailDrawer({ detail, open, onClose }: RiskDetailDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        className="w-full overflow-y-auto p-0 sm:!max-w-[540px]"
        style={{ width: "min(100vw, 540px)" }}
      >
        <SheetHeader className="sr-only">
          <SheetTitle>Collection detail</SheetTitle>
        </SheetHeader>
        {detail && <RiskDetailContent detail={detail} />}
      </SheetContent>
    </Sheet>
  );
}
