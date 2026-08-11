"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useSidebar } from "@/hooks/use-sidebar";
import { SIDEBAR_SECTIONS } from "./sidebar-nav-config";
import { SidebarNavItem } from "./sidebar-nav-item";
import { SidebarSection } from "./sidebar-section";

export function MobileSidebar() {
  const { mobileOpen, setMobileOpen } = useSidebar();

  if (!mobileOpen) return null;

  return (
    <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
      <SheetContent side="left" className="w-72 border-r border-sidebar-border bg-sidebar p-0">
        <SheetHeader className="h-14 justify-center border-b border-sidebar-border px-4">
          <SheetTitle className="text-base font-semibold tracking-tight">
            PayPredict
          </SheetTitle>
        </SheetHeader>
        <nav className="space-y-4 px-3 py-4">
          {SIDEBAR_SECTIONS.map((section) => (
            <SidebarSection key={section.title} title={section.title}>
              {section.items.map((item) => (
                <SidebarNavItem
                  key={item.href}
                  href={item.href}
                  icon={item.icon}
                  label={item.label}
                  description={item.description}
                  external={item.external}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </SidebarSection>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
