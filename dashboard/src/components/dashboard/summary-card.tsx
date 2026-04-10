"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  // Tailwind border-l-* class, e.g. "border-l-red-500"
  accentColor?: string;
  // Tailwind text-* class for the value, e.g. "text-red-400"
  valueColor?: string;
  active?: boolean;
  onClick?: () => void;
}

export function SummaryCard({
  title,
  value,
  subtitle,
  accentColor,
  valueColor,
  active = false,
  onClick,
}: SummaryCardProps) {
  return (
    <Card
      onClick={onClick}
      className={cn(
        "cursor-pointer border-l-4 transition-all hover:border-border/80",
        accentColor,
        active && "ring-2 ring-primary/40 bg-accent/30",
      )}
    >
      <CardContent className="p-5">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {title}
        </p>
        <p
          className={cn(
            "mt-2 text-4xl font-bold tabular-nums tracking-tight",
            valueColor ?? "text-foreground",
          )}
        >
          {value}
        </p>
        {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}
