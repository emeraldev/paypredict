import { cn } from "@/lib/utils";
import { getRiskConfig, type RiskLevel } from "@/lib/utils/format-risk";

interface RiskDotProps {
  level: RiskLevel;
  className?: string;
}

export function RiskDot({ level, className }: RiskDotProps) {
  const config = getRiskConfig(level);
  return (
    <span
      className={cn("inline-block h-2 w-2 rounded-full", config.dot, className)}
      aria-label={`${config.label} risk`}
    />
  );
}
