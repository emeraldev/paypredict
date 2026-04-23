"use client";

import { usePathname } from "next/navigation";
import { BellIcon, LogOutIcon, MenuIcon, SearchIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { useApi } from "@/hooks/use-api";
import { alertsApi } from "@/lib/api/alerts";
import { useSidebar } from "@/hooks/use-sidebar";
import { ThemeToggle } from "./theme-toggle";

const ROUTE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/dashboard/analytics": "Analytics",
  "/dashboard/outcomes": "Outcomes",
  "/dashboard/backtest": "Backtest",
  "/dashboard/settings": "Settings",
};

function getRouteTitle(pathname: string): string {
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname];
  // fallback: longest matching prefix
  const match = Object.keys(ROUTE_TITLES)
    .filter((p) => pathname.startsWith(p))
    .sort((a, b) => b.length - a.length)[0];
  return match ? ROUTE_TITLES[match] : "Dashboard";
}

export function Topbar() {
  const { setMobileOpen } = useSidebar();
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const title = getRouteTitle(pathname);
  const initials = user?.name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() ?? "?";

  const { data: alertsData } = useApi(() => alertsApi.list(), []);
  const unreadCount = alertsData?.unread_count ?? 0;

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-card/80 px-4 backdrop-blur-sm md:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Open menu"
      >
        <MenuIcon className="h-5 w-5" />
      </Button>

      <h1 className="text-lg font-semibold tracking-tight text-foreground">{title}</h1>

      <div className="ml-auto flex items-center gap-2">
        <div className="relative hidden md:block">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search..."
            className="h-9 w-56 rounded-lg pl-9 pr-12 text-sm"
          />
          <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            ⌘K
          </kbd>
        </div>

        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <BellIcon className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
              {unreadCount}
            </span>
          )}
        </Button>

        <ThemeToggle />

        <Avatar className="h-8 w-8">
          <AvatarFallback className="text-xs">{initials}</AvatarFallback>
        </Avatar>

        <Button
          variant="ghost"
          size="icon"
          onClick={logout}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOutIcon className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
