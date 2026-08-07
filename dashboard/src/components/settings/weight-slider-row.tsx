"use client";

import { Slider } from "@/components/ui/slider";
import { FACTOR_DESCRIPTIONS, FACTOR_LABELS } from "@/lib/constants";

interface WeightSliderRowProps {
  factorName: string;
  value: number; // 0-100 (percentage)
  onChange: (value: number) => void;
  disabled?: boolean;
  // Optional overrides — the weights API returns per-method labels +
  // descriptions and the tab passes them through. Fall back to the local
  // constants so any component still calling this row without them keeps
  // working (defensive during the API migration window).
  label?: string;
  description?: string;
}

export function WeightSliderRow({
  factorName,
  value,
  onChange,
  disabled,
  label: labelProp,
  description: descriptionProp,
}: WeightSliderRowProps) {
  const label = labelProp ?? FACTOR_LABELS[factorName] ?? factorName;
  const description = descriptionProp ?? FACTOR_DESCRIPTIONS[factorName] ?? "";

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
        disabled={disabled}
        onValueChange={(v) => {
          const next = Array.isArray(v) ? v[0] : v;
          onChange(next);
        }}
      />
    </div>
  );
}
