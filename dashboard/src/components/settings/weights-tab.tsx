"use client";

import { AlertCircleIcon, CheckCircle2Icon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpPopover } from "@/components/shared/help-popover";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@/hooks/use-auth";
import { configApi } from "@/lib/api/config";
import { WeightSliderRow } from "./weight-slider-row";

function toPercentMap(weights: { factor_name: string; weight: number }[]): Record<string, number> {
  return Object.fromEntries(weights.map((w) => [w.factor_name, Math.round(w.weight * 100)]));
}

export function WeightsTab() {
  const { data, loading, error } = useApi(() => configApi.getWeights(), []);
  const { isAdmin } = useAuth();
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [initialWeights, setInitialWeights] = useState<Record<string, number>>({});

  useEffect(() => {
    if (data) {
      const pctMap = toPercentMap(data.weights);
      setWeights(pctMap);
      setInitialWeights(pctMap);
    }
  }, [data]);

  if (loading) return <LoadingSkeleton variant="rows" count={8} />;
  if (error) return <p className="text-sm text-muted-foreground">Failed to load weights: {error}</p>;
  if (!data) return null;

  const total = Object.values(weights).reduce((sum, v) => sum + v, 0);
  const isValid = total === 100;

  const handleChange = (factor: string, value: number) => {
    setWeights((prev) => ({ ...prev, [factor]: value }));
  };

  const handleReset = () => {
    setWeights(initialWeights);
    toast.info("Weights reset to defaults");
  };

  const handleSave = async () => {
    if (!isValid) {
      toast.error("Weights must sum to 100%");
      return;
    }
    try {
      const payload: Record<string, number> = {};
      for (const [k, v] of Object.entries(weights)) {
        payload[k] = v / 100;
      }
      await configApi.updateWeights(payload);
      toast.success("Weights saved");
    } catch {
      toast.error("Failed to save weights");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Factor Weights</CardTitle>
        <p className="text-sm text-muted-foreground">
          The scoring engine combines 8 factors into a single 0–1 risk score.
          The sliders below control how much each factor contributes.
          Weights must sum to 100%. Larger weight = more influence on the
          final score.
          {isAdmin
            ? " Verify your changes with a backtest before saving — the Backtest tool re-scores past collections against the current weights."
            : " Read-only — only Admins can edit weights."}
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.weights.map((w) => (
          <WeightSliderRow
            key={w.factor_name}
            factorName={w.factor_name}
            value={weights[w.factor_name] ?? 0}
            onChange={(v) => handleChange(w.factor_name, v)}
            disabled={!isAdmin}
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
            <HelpPopover title="Why must weights sum to 100%?">
              <p>
                Each factor contributes a fraction of the final risk score. The
                weights are normalised, so the sum has to be exactly 100% for
                the maths to work out.
              </p>
              <p>
                If a factor doesn&apos;t apply to a given collection (e.g. card
                health on a wallet payment), the engine skips it and
                re-normalises the remaining weights for that score — but the
                base configuration here must still sum to 100%.
              </p>
            </HelpPopover>
          </div>
          {isAdmin && (
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleReset}>
                Discard changes
              </Button>
              <Button size="sm" onClick={handleSave} disabled={!isValid}>
                Save weights
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
