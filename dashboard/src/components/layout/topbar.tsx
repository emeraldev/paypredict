"use client";

import { BellIcon, MenuIcon, SearchIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSidebar } from "@/hooks/use-sidebar";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  const { setMobileOpen } = useSidebar();

  return (
    <header className="flex h-14 items-center gap-3 border-b border-border bg-card px-4 md:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Open menu"
      >
        <MenuIcon className="h-5 w-5" />
      </Button>

      <div className="relative hidden flex-1 max-w-md md:block">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search collections, customers..." className="pl-9" />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <BellIcon className="h-5 w-5" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
        </Button>
        <Avatar className="h-8 w-8">
          <AvatarFallback className="text-xs">SA</AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
