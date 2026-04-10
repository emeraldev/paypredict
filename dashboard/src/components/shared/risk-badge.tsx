import { cn } from "@/lib/utils";
import { getRiskConfig, type RiskLevel } from "@/lib/utils/format-risk";

interface RiskBadgeProps {
  level: RiskLevel;
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  const config = getRiskConfig(level);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        config.bg,
        config.color,
        config.border,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
