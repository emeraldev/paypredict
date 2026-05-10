"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOutIcon, MenuIcon, SearchIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { useAuth } from "@/hooks/use-auth";
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
  const [paletteOpen, setPaletteOpen] = useState(false);

  const title = getRouteTitle(pathname);
  const initials = user?.name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() ?? "?";

  // Cmd+K / Ctrl+K opens the command palette from anywhere
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <>
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
          {/* Command palette trigger — looks like a search input but opens the palette */}
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="relative hidden h-9 w-56 items-center gap-2 rounded-lg border border-border bg-card pl-3 pr-2 text-left text-sm text-muted-foreground transition-colors hover:bg-accent/30 hover:text-foreground md:flex"
            aria-label="Open command palette"
          >
            <SearchIcon className="h-4 w-4 shrink-0" />
            <span className="flex-1 truncate">Search...</span>
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              ⌘K
            </kbd>
          </button>

          <NotificationBell />

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

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
