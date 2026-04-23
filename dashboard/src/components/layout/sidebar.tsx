"use client";

import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  FileCodeIcon,
  ShieldCheckIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useSidebar } from "@/hooks/use-sidebar";
import { NAV_ITEMS } from "./sidebar-nav-config";
import { SidebarNavItem } from "./sidebar-nav-item";

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
        "hidden h-screen shrink-0 border-r border-border bg-card transition-[width] duration-200 md:flex md:flex-col",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div
        className={cn(
          "flex h-14 items-center border-b border-border px-4",
          collapsed && "justify-center px-2",
        )}
      >
        <ShieldCheckIcon className="h-5 w-5 shrink-0 text-primary" />
        {!collapsed && (
          <span className="ml-2 text-base font-semibold tracking-tight">PayPredict</span>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV_ITEMS.map((item) => (
          <SidebarNavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            collapsed={collapsed}
          />
        ))}
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground",
            collapsed && "justify-center px-2",
          )}
          title={collapsed ? "API Docs" : undefined}
        >
          <FileCodeIcon className="h-4 w-4 shrink-0" />
          {!collapsed && (
            <>
              <span>API Docs</span>
              <ExternalLinkIcon className="ml-auto h-3.5 w-3.5 text-muted-foreground/70" />
            </>
          )}
        </a>
      </nav>

      {/* Tenant info block */}
      <div
        className={cn(
          "border-t border-border px-3 py-3",
          collapsed && "flex justify-center px-2",
        )}
      >
        <div className={cn("flex items-center gap-3", collapsed && "gap-0")}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold text-foreground">
            {tenant ? initialsFromName(tenant.name) : "?"}
          </div>
          {!collapsed && tenant && (
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-foreground">
                  {tenant.name}
                </span>
                <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0 text-[10px] font-medium text-emerald-400">
                  {PLAN_LABEL[tenant.plan] ?? tenant.plan}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">{user?.role ?? ""}</span>
            </div>
          )}
        </div>
      </div>

      <div className={cn("border-t border-border p-3", collapsed && "px-2")}>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggle}
          className={cn("w-full justify-start gap-2", collapsed && "justify-center")}
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
