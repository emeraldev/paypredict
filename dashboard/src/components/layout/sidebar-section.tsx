"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface SidebarSectionProps {
  title: string;
  collapsed?: boolean;
  children: ReactNode;
}

export function SidebarSection({ title, collapsed = false, children }: SidebarSectionProps) {
  return (
    <div className="space-y-1">
      {!collapsed && (
        <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
          {title}
        </div>
      )}
      <div className={cn("space-y-0.5", collapsed && "pt-3 first:pt-0")}>{children}</div>
    </div>
  );
}
