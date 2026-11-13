"use client";

import { AlertTriangle, Check, ChevronsUpDown } from "lucide-react";
import * as React from "react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface Suggestion {
  value: string;
  label: string;
  group: "Buckets" | "Zambian employers";
}

// Mirrors the backend alias table in
// api/app/scoring/factors/payroll/borrower_segment.py. Keep in sync:
// anything the backend aliases to a bucket should appear here so the
// officer sees the recognised name in the list.
const SUGGESTIONS: ReadonlyArray<Suggestion> = [
  { value: "government", label: "Government", group: "Buckets" },
  { value: "private_sector", label: "Private sector", group: "Buckets" },
  { value: "contract", label: "Contract", group: "Buckets" },
  { value: "mining", label: "Mining", group: "Buckets" },
  { value: "informal", label: "Informal", group: "Buckets" },
  { value: "ZESCO", label: "ZESCO (utility)", group: "Zambian employers" },
  { value: "KCM", label: "KCM (mine)", group: "Zambian employers" },
  { value: "Mopani", label: "Mopani (mine)", group: "Zambian employers" },
  { value: "FQM", label: "FQM (mine)", group: "Zambian employers" },
];

// Known values the backend DOES NOT fall through to the 0.4 default on.
// Used to decide whether to show the "unrecognised, scored as moderate"
// hint below the field.
const RECOGNISED_LOWER = new Set(
  SUGGESTIONS.map((s) => s.value.toLowerCase()),
);

interface BorrowerSegmentComboboxProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
}

export function BorrowerSegmentCombobox({
  value,
  onChange,
  placeholder = "Pick or type an employer...",
  maxLength = 32,
}: BorrowerSegmentComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");

  const displayed = SUGGESTIONS.find(
    (s) => s.value.toLowerCase() === value.toLowerCase(),
  )?.label;

  const isUnrecognised =
    value.trim().length > 0 &&
    !RECOGNISED_LOWER.has(value.toLowerCase());

  const commit = (next: string) => {
    onChange(next.slice(0, maxLength));
    setSearch("");
    setOpen(false);
  };

  // Group entries for the two-section list.
  const bucketItems = SUGGESTIONS.filter((s) => s.group === "Buckets");
  const employerItems = SUGGESTIONS.filter((s) => s.group === "Zambian employers");

  const trimmed = search.trim();
  const showAddCustom =
    trimmed.length > 0 &&
    !SUGGESTIONS.some(
      (s) => s.value.toLowerCase() === trimmed.toLowerCase(),
    );

  return (
    <div className="space-y-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          type="button"
          role="combobox"
          aria-expanded={open}
          // Classes mirror SelectTrigger (shadcn / base-ui variant) so
          // this combobox sits visually in the same row as other
          // selects / inputs on the form. When the current value is
          // not in the recognised set, the trigger flips to an amber
          // warning state (not destructive-red; the value is unknown,
          // not invalid, and the score still comes back as 0.4
          // moderate). Border, tinted background, warning text colour
          // and an inline AlertTriangle icon together ensure a loan
          // officer cannot miss that they are about to score an
          // unrecognised employer with the fallback prior.
          className={cn(
            "flex h-9 w-full items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent py-2 pr-2 pl-3 text-sm whitespace-nowrap transition-colors outline-none select-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 dark:bg-input/30 dark:hover:bg-input/50",
            !value && "text-muted-foreground",
            isUnrecognised &&
              "border-amber-500 bg-amber-50 text-amber-900 focus-visible:border-amber-500 focus-visible:ring-amber-500/40 dark:border-amber-500/70 dark:bg-amber-500/10 dark:text-amber-200",
          )}
        >
          <span className="flex min-w-0 items-center gap-1.5 truncate">
            {isUnrecognised && (
              <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
            )}
            <span className="truncate">
              {displayed ?? value ?? placeholder}
            </span>
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </PopoverTrigger>
        <PopoverContent
          className="w-[--radix-popover-trigger-width] min-w-[260px] p-0"
          align="start"
        >
          <Command>
            <CommandInput
              placeholder="Search or type any employer..."
              value={search}
              onValueChange={setSearch}
              maxLength={maxLength}
            />
            <CommandList>
              <CommandEmpty>
                {trimmed ? `Press Enter to use "${trimmed}"` : "No matches"}
              </CommandEmpty>

              <CommandGroup heading="Buckets">
                {bucketItems.map((s) => (
                  <CommandItem
                    key={s.value}
                    value={s.value}
                    onSelect={() => commit(s.value)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value.toLowerCase() === s.value.toLowerCase()
                          ? "opacity-100"
                          : "opacity-0",
                      )}
                    />
                    {s.label}
                  </CommandItem>
                ))}
              </CommandGroup>

              <CommandGroup heading="Zambian employers">
                {employerItems.map((s) => (
                  <CommandItem
                    key={s.value}
                    value={s.value}
                    onSelect={() => commit(s.value)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value.toLowerCase() === s.value.toLowerCase()
                          ? "opacity-100"
                          : "opacity-0",
                      )}
                    />
                    {s.label}
                  </CommandItem>
                ))}
              </CommandGroup>

              {showAddCustom && (
                <CommandGroup heading="Custom">
                  <CommandItem
                    value={`__custom__${trimmed}`}
                    onSelect={() => commit(trimmed)}
                  >
                    Use &quot;{trimmed}&quot;
                  </CommandItem>
                </CommandGroup>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {isUnrecognised && (
        <p className="flex items-start gap-1.5 text-xs font-medium text-amber-700 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>
            Not in the recognised list. This employer will score as moderate
            (0.4). Pick a bucket or a known employer for a calibrated prior.
          </span>
        </p>
      )}
    </div>
  );
}
