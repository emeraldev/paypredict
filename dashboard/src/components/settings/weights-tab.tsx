"use client";

import { AlertCircleIcon, CheckCircle2Icon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { mockWeights } from "@/lib/mock-data";
import { WeightSliderRow } from "./weight-slider-row";

// Convert stored fractional weights (0-1) to slider percentages (0-100)
function toPercentMap(weights: typeof mockWeights.weights): Record<string, number> {
  return Object.fromEntries(weights.map((w) => [w.factor_name, Math.round(w.weight * 100)]));
}

const initialWeights = toPercentMap(mockWeights.weights);

export function WeightsTab() {
  const [weights, setWeights] = useState<Record<string, number>>(initialWeights);

  const total = Object.values(weights).reduce((sum, v) => sum + v, 0);
  const isValid = total === 100;

  const handleChange = (factor: string, value: number) => {
    setWeights((prev) => ({ ...prev, [factor]: value }));
  };

  const handleReset = () => {
    setWeights(initialWeights);
    toast.info("Weights reset to defaults");
  };

  const handleSave = () => {
    if (!isValid) {
      toast.error("Weights must sum to 100%");
      return;
    }
    toast.success("Weights saved");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Factor Weights</CardTitle>
        <p className="text-sm text-muted-foreground">
          Adjust how much each factor contributes to the final risk score. Total must equal 100%.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {mockWeights.weights.map((w) => (
          <WeightSliderRow
            key={w.factor_name}
            factorName={w.factor_name}
            value={weights[w.factor_name] ?? 0}
            onChange={(v) => handleChange(w.factor_name, v)}
          />
        ))}

        <div className="flex items-center justify-between border-t border-border pt-4">
          <div className="flex items-center gap-2 text-sm">
            {isValid ? (
              <CheckCircle2Icon className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircleIcon className="h-4 w-4 text-amber-400" />
            )}
            <span className="text-muted-foreground">Total:</span>
            <span className={cn("font-mono tabular-nums font-medium", !isValid && "text-amber-400")}>
              {total}%
            </span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleReset}>
              Reset to defaults
            </Button>
            <Button size="sm" onClick={handleSave} disabled={!isValid}>
              Save weights
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
