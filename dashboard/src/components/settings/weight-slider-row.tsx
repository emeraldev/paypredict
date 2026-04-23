"use client";

import { Slider } from "@/components/ui/slider";
import { FACTOR_DESCRIPTIONS, FACTOR_LABELS } from "@/lib/constants";

interface WeightSliderRowProps {
  factorName: string;
  value: number; // 0-100 (percentage)
  onChange: (value: number) => void;
}

export function WeightSliderRow({ factorName, value, onChange }: WeightSliderRowProps) {
  const label = FACTOR_LABELS[factorName] ?? factorName;
  const description = FACTOR_DESCRIPTIONS[factorName] ?? "";

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <span className="text-sm font-mono tabular-nums text-foreground">{value}%</span>
      </div>
      <Slider
        value={[value]}
        max={50}
        min={0}
        step={1}
        onValueChange={(v) => {
          const next = Array.isArray(v) ? v[0] : v;
          onChange(next);
        }}
      />
    </div>
  );
}
