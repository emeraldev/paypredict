import { cn } from "@/lib/utils";
import { displayScore, getRiskConfig, type RiskLevel } from "@/lib/utils/format-risk";
import { RiskDot } from "./risk-dot";

interface RiskScoreDisplayProps {
  // Score in 0.0-1.0 range (raw model output)
  score: number;
  riskLevel: RiskLevel;
  // Show the mini horizontal bar (default true)
  showBar?: boolean;
  className?: string;
}

export function RiskScoreDisplay({
  score,
  riskLevel,
  showBar = true,
  className,
}: RiskScoreDisplayProps) {
  const config = getRiskConfig(riskLevel);
  const display = displayScore(score);

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <RiskDot level={riskLevel} />
      <span className={cn("font-mono text-sm tabular-nums", config.color)}>{display}</span>
      {showBar && (
        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${display}%`,
              backgroundColor: config.barColor,
            }}
          />
        </div>
      )}
    </div>
  );
}
