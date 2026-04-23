import type { FactorBreakdown as FactorBreakdownType } from "@/lib/api/types";
import { FactorBar } from "./factor-bar";

interface FactorBreakdownProps {
  factors: FactorBreakdownType[];
  skippedFactors?: string[];
}

export function FactorBreakdown({ factors, skippedFactors = [] }: FactorBreakdownProps) {
  const sorted = [...factors].sort((a, b) => b.weighted_score - a.weighted_score);

  return (
    <div className="space-y-5">
      {sorted.map((f) => (
        <FactorBar
          key={f.factor}
          factor={f.factor}
          rawScore={f.raw_score}
          weight={f.weight}
          weightedScore={f.weighted_score}
          explanation={f.explanation}
        />
      ))}
      {skippedFactors.length > 0 && (
        <div className="rounded-md border border-dashed border-border bg-muted/40 p-3">
          <p className="text-xs font-medium text-muted-foreground">
            Skipped for this collection method
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{skippedFactors.join(", ")}</p>
        </div>
      )}
    </div>
  );
}
