import { ArrowDownIcon, ArrowUpIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number; // percentage, positive or negative
    label?: string;
  };
  accentColor?: string; // Tailwind border color class, e.g. "border-l-red-500"
  icon?: React.ReactNode;
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  trend,
  accentColor,
  icon,
  className,
}: StatCardProps) {
  const trendUp = trend && trend.value >= 0;
  const TrendIcon = trendUp ? ArrowUpIcon : ArrowDownIcon;

  return (
    <Card className={cn(accentColor && `border-l-4 ${accentColor}`, className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-semibold tracking-tight">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {icon && <div className="text-muted-foreground">{icon}</div>}
        </div>
        {trend && (
          <div className="mt-4 flex items-center gap-1.5 text-xs">
            <TrendIcon
              className={cn("h-3 w-3", trendUp ? "text-emerald-400" : "text-red-400")}
            />
            <span className={trendUp ? "text-emerald-400" : "text-red-400"}>
              {Math.abs(trend.value)}%
            </span>
            {trend.label && <span className="text-muted-foreground">{trend.label}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
