import { FACTOR_LABELS, getTriggerLabel } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { getFactorBarClass } from "@/lib/utils/format-risk";

interface FactorBarProps {
  factor: string;
  rawScore: number;
  weight: number;
  weightedScore: number;
  explanation: string;
  trigger?: string | null;
  className?: string;
}

export function FactorBar({
  factor,
  rawScore,
  weight,
  weightedScore,
  explanation,
  trigger,
  className,
}: FactorBarProps) {
  const label = FACTOR_LABELS[factor] ?? factor;
  const barClass = getFactorBarClass(rawScore);
  // Min 3% width so non-zero scores are still visible
  const barWidth = Math.max(Math.round(rawScore * 100), 3);
  const triggerLabel = getTriggerLabel(trigger);

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-foreground">{label}</span>
        <div className="flex items-baseline gap-2 text-xs">
          <span className="font-mono font-semibold tabular-nums text-foreground">
            {rawScore.toFixed(2)}
          </span>
          <span className="text-muted-foreground">×{Math.round(weight * 100)}%</span>
          <span className="font-mono tabular-nums text-muted-foreground">
            ={weightedScore.toFixed(3)}
          </span>
        </div>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", barClass)}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">{explanation}</p>
      {triggerLabel && (
        <span className="inline-flex items-center rounded-md border border-destructive/30 bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-destructive">
          {triggerLabel}
        </span>
      )}
    </div>
  );
}
