"use client";

import type { ReactNode } from "react";
import { XIcon } from "lucide-react";

interface FilterChipProps {
  /** The label shown in the chip. Include the field name (e.g. "Risk: High"). */
  label: string;
  /** Click handler that clears the underlying filter. */
  onClear: () => void;
}

/**
 * Rounded pill that surfaces one active filter with a clear affordance.
 * Compose inside `<FilterChipBar>` for multiple simultaneous filters.
 */
export function FilterChip({ label, onClear }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClear}
      className="inline-flex items-center gap-2 rounded-full bg-sidebar-accent px-3 py-1 text-xs text-sidebar-accent-foreground transition-colors hover:bg-primary/15"
    >
      <span>{label}</span>
      <XIcon className="h-3 w-3" />
    </button>
  );
}

interface FilterChipBarProps {
  children: ReactNode;
  /** Optional "Clear all" affordance. Rendered when supplied and there is
   *  more than one chip in `children`. */
  onClearAll?: () => void;
}

/**
 * Horizontal container for a row of `<FilterChip>` elements.
 * Wraps on narrow viewports. Include a `Clear all` on the right when
 * two or more filters are active.
 */
export function FilterChipBar({ children, onClearAll }: FilterChipBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {children}
      {onClearAll && (
        <button
          type="button"
          onClick={onClearAll}
          className="text-xs font-medium text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
