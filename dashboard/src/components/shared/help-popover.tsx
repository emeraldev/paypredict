"use client";

import type { ReactNode } from "react";
import { HelpCircleIcon } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface HelpPopoverProps {
  /** Short title shown bold at the top of the popover. */
  title: string;
  /** Body content — plain text, a string, or rich JSX. */
  children: ReactNode;
  /** Accessible label for the trigger button. Defaults to `Help: <title>`. */
  ariaLabel?: string;
  /** Override the popover width. Defaults to shadcn's `w-72` (288px). */
  className?: string;
}

/**
 * A small "?" icon that opens a popover with a short title + body.
 *
 * Used to surface contextual explanations of jargon-y UI elements
 * without forcing the user to leave the page. The icon button is
 * deliberately quiet (muted-foreground until hover) so it doesn't
 * compete with the surrounding content visually — it's *available*
 * help, not *demanded* help.
 */
export function HelpPopover({
  title,
  children,
  ariaLabel,
  className,
}: HelpPopoverProps) {
  return (
    <Popover>
      <PopoverTrigger
        type="button"
        aria-label={ariaLabel ?? `Help: ${title}`}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground/70 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        <HelpCircleIcon className="h-4 w-4" />
      </PopoverTrigger>
      <PopoverContent className={cn("w-80", className)} side="top">
        <PopoverHeader>
          <PopoverTitle>{title}</PopoverTitle>
        </PopoverHeader>
        <div className="space-y-2 text-xs leading-relaxed text-muted-foreground">
          {children}
        </div>
      </PopoverContent>
    </Popover>
  );
}
