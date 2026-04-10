"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  accentColor?: string; // e.g. "border-l-red-500"
  active?: boolean;
  onClick?: () => void;
}

export function SummaryCard({
  title,
  value,
  subtitle,
  accentColor,
  active = false,
  onClick,
}: SummaryCardProps) {
  return (
    <Card
      onClick={onClick}
      className={cn(
        "cursor-pointer border-l-4 transition-all hover:bg-accent/40",
        accentColor,
        active && "ring-2 ring-primary/40 bg-accent/30",
      )}
    >
      <CardContent className="p-5">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="mt-1 text-3xl font-semibold tracking-tight">{value}</p>
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
