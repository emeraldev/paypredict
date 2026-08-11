"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ExternalLinkIcon, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarNavItemProps {
  href: string;
  icon: LucideIcon;
  label: string;
  description?: string;
  external?: boolean;
  collapsed?: boolean;
  onClick?: () => void;
}

export function SidebarNavItem({
  href,
  icon: Icon,
  label,
  description,
  external = false,
  collapsed = false,
  onClick,
}: SidebarNavItemProps) {
  const pathname = usePathname();
  const active = !external && (pathname === href || (href !== "/dashboard" && pathname.startsWith(href)));

  const className = cn(
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
    active
      ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
      : "text-muted-foreground hover:bg-muted hover:text-foreground",
    collapsed && "justify-center px-2",
  );

  const content = (
    <>
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{label}</span>
          {external && (
            <ExternalLinkIcon className="h-3.5 w-3.5 text-muted-foreground/70" />
          )}
        </>
      )}
    </>
  );

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        onClick={onClick}
        className={className}
        title={collapsed ? label : description}
      >
        {content}
      </a>
    );
  }

  return (
    <Link
      href={href}
      onClick={onClick}
      className={className}
      title={collapsed ? label : description}
    >
      {content}
    </Link>
  );
}
