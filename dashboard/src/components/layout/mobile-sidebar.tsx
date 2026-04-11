"use client";

import { ExternalLinkIcon, FileCodeIcon, ShieldCheckIcon } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useSidebar } from "@/hooks/use-sidebar";
import { NAV_ITEMS } from "./sidebar-nav-config";
import { SidebarNavItem } from "./sidebar-nav-item";

export function MobileSidebar() {
  const { mobileOpen, setMobileOpen } = useSidebar();

  return (
    <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader className="border-b border-border p-4">
          <SheetTitle className="flex items-center gap-2">
            <ShieldCheckIcon className="h-5 w-5 text-primary" />
            <span>PayPredict</span>
          </SheetTitle>
        </SheetHeader>
        <nav className="space-y-1 p-3">
          {NAV_ITEMS.map((item) => (
            <SidebarNavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              onClick={() => setMobileOpen(false)}
            />
          ))}
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
          >
            <FileCodeIcon className="h-4 w-4 shrink-0" />
            <span>API Docs</span>
            <ExternalLinkIcon className="ml-auto h-3.5 w-3.5 text-muted-foreground/70" />
          </a>
        </nav>
      </SheetContent>
    </Sheet>
  );
}
