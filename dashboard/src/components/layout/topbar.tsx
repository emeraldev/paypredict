"use client";

import { useEffect, useState } from "react";
import { LogOutIcon, MenuIcon, SearchIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { useAuth } from "@/hooks/use-auth";
import { useSidebar } from "@/hooks/use-sidebar";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  const { setMobileOpen } = useSidebar();
  const { user, logout } = useAuth();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const initials = user?.name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() ?? "?";

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
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 bg-brand px-4 text-brand-foreground md:px-6">
        <Button
          variant="ghost"
          size="icon"
          className="text-brand-foreground hover:bg-white/10 hover:text-brand-foreground focus-visible:border-white/60 focus-visible:ring-white/40 md:hidden"
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
        >
          <MenuIcon className="h-5 w-5" />
        </Button>

        <span className="text-base font-bold tracking-tight">PayPredict</span>

        <div className="ml-auto flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="relative hidden h-9 w-56 items-center gap-2 rounded-md bg-white/10 pl-3 pr-2 text-left text-sm text-brand-foreground/80 outline-none transition-colors hover:bg-white/15 hover:text-brand-foreground focus-visible:ring-2 focus-visible:ring-white/50 md:flex"
            aria-label="Open command palette"
          >
            <SearchIcon className="h-4 w-4 shrink-0" />
            <span className="flex-1 truncate">Search...</span>
            <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-brand-foreground/80">
              ⌘K
            </kbd>
          </button>

          <div className="[&_button]:text-brand-foreground [&_button]:hover:bg-white/10 [&_button]:hover:text-brand-foreground [&_button]:focus-visible:border-white/60 [&_button]:focus-visible:ring-white/40">
            <NotificationBell />
          </div>

          <div className="[&_button]:text-brand-foreground [&_button]:hover:bg-white/10 [&_button]:hover:text-brand-foreground [&_button]:focus-visible:border-white/60 [&_button]:focus-visible:ring-white/40">
            <ThemeToggle />
          </div>

          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-white/15 text-xs text-brand-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>

          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            aria-label="Sign out"
            title="Sign out"
            className="text-brand-foreground hover:bg-white/10 hover:text-brand-foreground focus-visible:border-white/60 focus-visible:ring-white/40"
          >
            <LogOutIcon className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
