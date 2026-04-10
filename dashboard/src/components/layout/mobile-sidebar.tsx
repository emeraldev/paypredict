"use client";

import { ShieldCheckIcon } from "lucide-react";
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
        </nav>
      </SheetContent>
    </Sheet>
  );
}
