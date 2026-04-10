import { cn } from "@/lib/utils";
import { FACTOR_LABELS } from "@/lib/constants";
import { getFactorBarColor } from "@/lib/utils/format-risk";

interface FactorBarProps {
  factor: string;
  rawScore: number;
  weight: number;
  weightedScore: number;
  explanation: string;
  className?: string;
}

export function FactorBar({
  factor,
  rawScore,
  weight,
  weightedScore,
  explanation,
  className,
}: FactorBarProps) {
  const label = FACTOR_LABELS[factor] ?? factor;
  const barColor = getFactorBarColor(rawScore);
  const barWidth = Math.round(rawScore * 100);

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <div className="flex items-baseline gap-2 text-xs">
          <span className="font-mono tabular-nums text-foreground">{rawScore.toFixed(2)}</span>
          <span className="text-muted-foreground">× {weight.toFixed(2)}</span>
          <span className="font-mono tabular-nums text-muted-foreground">
            = {weightedScore.toFixed(3)}
          </span>
        </div>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${barWidth}%`,
            backgroundColor: barColor,
          }}
        />
      </div>
      <p className="text-xs text-muted-foreground">{explanation}</p>
    </div>
  );
}
