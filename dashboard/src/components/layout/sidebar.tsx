"use client";

import {
  ChevronLeftIcon,
  ChevronRightIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useSidebar } from "@/hooks/use-sidebar";
import { SIDEBAR_SECTIONS } from "./sidebar-nav-config";
import { SidebarNavItem } from "./sidebar-nav-item";
import { SidebarSection } from "./sidebar-section";

const PLAN_LABEL: Record<string, string> = {
  PILOT: "Pilot",
  STARTER: "Starter",
  GROWTH: "Growth",
  SCALE: "Scale",
};

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const { user } = useAuth();
  const tenant = user?.tenant;

  return (
    <aside
      className={cn(
        "hidden h-full shrink-0 border-r border-sidebar-border bg-sidebar transition-[width] duration-200 md:flex md:flex-col",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {SIDEBAR_SECTIONS.map((section) => (
          <SidebarSection key={section.title} title={section.title} collapsed={collapsed}>
            {section.items.map((item) => (
              <SidebarNavItem
                key={item.href}
                href={item.href}
                icon={item.icon}
                label={item.label}
                description={item.description}
                external={item.external}
                collapsed={collapsed}
              />
            ))}
          </SidebarSection>
        ))}
      </nav>

      {tenant && (
        <div
          className={cn(
            "border-t border-sidebar-border px-3 py-3",
            collapsed && "flex justify-center px-2",
          )}
        >
          {collapsed ? (
            <div
              className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-xs font-semibold text-foreground"
              title={tenant.name}
            >
              {initialsFromName(tenant.name)}
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-foreground">
                  {tenant.name}
                </div>
                <div className="text-xs text-muted-foreground">{user?.role ?? ""}</div>
              </div>
              <span className="rounded-full bg-sidebar-accent px-2 py-0.5 text-[10px] font-semibold text-sidebar-accent-foreground">
                {PLAN_LABEL[tenant.plan] ?? tenant.plan}
              </span>
            </div>
          )}
        </div>
      )}

      <div className={cn("border-t border-sidebar-border p-2", collapsed && "px-1")}>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggle}
          className={cn(
            "w-full justify-start gap-2 text-muted-foreground",
            collapsed && "justify-center",
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRightIcon className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeftIcon className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}

function initialsFromName(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}
