"use client";

import { AlertCircleIcon, CheckCircle2Icon, PlusIcon, SlidersHorizontalIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/empty-state";
import { HelpPopover } from "@/components/shared/help-popover";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@/hooks/use-auth";
import { configApi } from "@/lib/api/config";
import { METHOD_CONFIG } from "@/lib/constants";
import type { WeightsMethodEntry, WeightsResponse } from "@/lib/api/types";
import type { CollectionMethod } from "@/lib/utils/format-method";
import { WeightSliderRow } from "./weight-slider-row";

// Every method the backend registry knows about. The tab strip normally
// shows only the subset the tenant actually uses; the "+ Add method"
// menu below offers whatever's missing.
const ALL_METHODS: readonly CollectionMethod[] = [
  "CARD",
  "DEBIT_ORDER",
  "MOBILE_MONEY",
  "PAYROLL",
] as const;

type MethodDraft = {
  values: Record<string, number>;
  initial: Record<string, number>;
};

// Convert the API's 0-1 float weights into the 0-100 integer percentages
// the sliders expect. Round to keep the total on a whole-number boundary.
function toPercentMap(entry: WeightsMethodEntry): Record<string, number> {
  return Object.fromEntries(
    entry.factors.map((f) => [f.factor_name, Math.round(f.weight * 100)]),
  );
}

function isDirty(draft: MethodDraft | undefined) {
  if (!draft) return false;
  return Object.keys(draft.values).some(
    (k) => draft.values[k] !== draft.initial[k],
  );
}

/**
 * Merge a fresh API response into the current per-method drafts.
 *
 * A tab that has unsaved user edits KEEPS its local draft untouched
 * (both `values` and `initial`) so the amber dirty-dot stays honest
 * and the user's in-progress edits don't vanish when a save on another
 * tab triggers `refetch()` — H6. A clean tab (or a method we didn't
 * have local state for yet) refreshes both fields from the server so
 * a concurrent edit from another admin surfaces on the next render.
 *
 * Methods present in `prev` but absent from `data` are dropped —
 * their tab is going away anyway.
 */
function mergeResponseIntoDrafts(
  prev: Record<CollectionMethod, MethodDraft>,
  data: WeightsResponse,
): Record<CollectionMethod, MethodDraft> {
  const next = {} as Record<CollectionMethod, MethodDraft>;
  for (const entry of data.methods) {
    const method = entry.collection_method;
    const existing = prev[method];
    if (existing && isDirty(existing)) {
      next[method] = existing;
      continue;
    }
    const serverPct = toPercentMap(entry);
    next[method] = { values: serverPct, initial: serverPct };
  }
  return next;
}

function methodTotal(draft: MethodDraft | undefined) {
  if (!draft) return 0;
  return Object.values(draft.values).reduce((sum, v) => sum + v, 0);
}

export function WeightsTab() {
  const { data, loading, error, refetch } = useApi(() => configApi.getWeights(), []);
  const { isAdmin } = useAuth();
  const router = useRouter();

  const [drafts, setDrafts] = useState<Record<CollectionMethod, MethodDraft>>(
    {} as Record<CollectionMethod, MethodDraft>,
  );
  const [activeMethod, setActiveMethod] = useState<CollectionMethod | null>(null);
  const [savingMethod, setSavingMethod] = useState<CollectionMethod | null>(null);
  const [addingMethod, setAddingMethod] = useState<CollectionMethod | null>(null);

  const methods = useMemo<WeightsMethodEntry[]>(
    () => data?.methods ?? [],
    [data],
  );

  // Methods the tenant does NOT yet have a tab for — offered in the
  // "+ Add method" menu so a lender preparing to expand into a new
  // method can pre-configure its weights before the first collection.
  const availableToAdd = useMemo<CollectionMethod[]>(
    () => ALL_METHODS.filter(
      (m) => !methods.some((entry) => entry.collection_method === m),
    ),
    [methods],
  );

  const handleAddMethod = async (method: CollectionMethod) => {
    try {
      setAddingMethod(method);
      await configApi.addWeightsMethod(method);
      toast.success(`${METHOD_CONFIG[method].label} tab added`);
      setActiveMethod(method);
      refetch();
    } catch {
      toast.error("Failed to add method");
    } finally {
      setAddingMethod(null);
    }
  };

  useEffect(() => {
    if (!data) return;
    // Merge in place: dirty tabs keep their local edits (H6 fix),
    // clean tabs refresh from the server, new methods initialise from
    // the server, deleted methods drop out.
    setDrafts((prev) => mergeResponseIntoDrafts(prev, data));
    // Only initialise activeMethod once — don't stomp the user's tab
    // selection when a refetch lands after a save.
    setActiveMethod((prev) => prev ?? data.methods[0]?.collection_method ?? null);
  }, [data]);

  if (loading) return <LoadingSkeleton variant="rows" count={8} />;
  if (error) {
    return (
      <p className="text-sm text-muted-foreground">Failed to load weights: {error}</p>
    );
  }
  if (!data) return null;

  if (methods.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={<SlidersHorizontalIcon className="h-6 w-6" />}
            title="No weights to tune yet"
            description={
              isAdmin
                ? "Weights appear here per collection method. Score a collection with a method to open its tab, or add one below to pre-configure defaults before you start collecting."
                : "Weights appear here per collection method once your tenant has scored at least one collection."
            }
            action={
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button size="sm" onClick={() => router.push("/dashboard/score")}>
                  Score a collection
                </Button>
                {isAdmin && availableToAdd.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={
                        <Button variant="outline" size="sm">
                          <PlusIcon className="mr-1 h-4 w-4" />
                          Add method
                        </Button>
                      }
                    />
                    <DropdownMenuContent align="center">
                      <DropdownMenuGroup>
                        <DropdownMenuLabel>Add method tab</DropdownMenuLabel>
                        {availableToAdd.map((m) => (
                          <DropdownMenuItem
                            key={m}
                            disabled={addingMethod !== null}
                            onClick={() => handleAddMethod(m)}
                          >
                            {METHOD_CONFIG[m].label}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuGroup>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            }
          />
        </CardContent>
      </Card>
    );
  }

  const currentMethod = activeMethod ?? methods[0].collection_method;
  const currentEntry = methods.find((m) => m.collection_method === currentMethod) ?? methods[0];
  const currentDraft = drafts[currentEntry.collection_method];

  const handleChange = (method: CollectionMethod, factor: string, value: number) => {
    setDrafts((prev) => ({
      ...prev,
      [method]: {
        initial: prev[method]?.initial ?? {},
        values: { ...(prev[method]?.values ?? {}), [factor]: value },
      },
    }));
  };

  const handleReset = (method: CollectionMethod) => {
    setDrafts((prev) => ({
      ...prev,
      [method]: {
        initial: prev[method]?.initial ?? {},
        values: { ...(prev[method]?.initial ?? {}) },
      },
    }));
    toast.info("Changes discarded");
  };

  const handleSave = async (method: CollectionMethod, entry: WeightsMethodEntry) => {
    const draft = drafts[method];
    if (!draft) return;
    if (methodTotal(draft) !== 100) {
      toast.error("Weights must sum to 100%");
      return;
    }
    const payload: Record<string, number> = {};
    for (const [k, v] of Object.entries(draft.values)) {
      payload[k] = v / 100;
    }
    try {
      setSavingMethod(method);
      await configApi.updateWeights(method, payload);
      toast.success(`${entry.method_label} weights saved`);
      // Reset the dirty baseline for this tab; other tabs' unsaved edits
      // are preserved because the API only touched this method's rows.
      setDrafts((prev) => ({
        ...prev,
        [method]: { values: draft.values, initial: draft.values },
      }));
      refetch();
    } catch {
      toast.error("Failed to save weights");
    } finally {
      setSavingMethod(null);
    }
  };

  const currentTotal = methodTotal(currentDraft);
  const currentValid = currentTotal === 100;
  const currentDirty = isDirty(currentDraft);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Factor Weights</CardTitle>
        <p className="text-sm text-muted-foreground">
          Each collection method has its own weights. Changes on one tab only
          affect scoring for that method&apos;s collections.
          {isAdmin
            ? " Verify your changes with a backtest before saving. The Backtest tool re-scores past collections against the current weights."
            : " Read-only. Only Admins can edit weights."}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs
          value={currentMethod}
          onValueChange={(v) => setActiveMethod(v as CollectionMethod)}
        >
          <div className="flex items-center gap-2">
            <TabsList>
              {methods.map((m) => {
                const dirty = isDirty(drafts[m.collection_method]);
                return (
                  <TabsTrigger
                    key={m.collection_method}
                    value={m.collection_method}
                    className="data-active:bg-primary data-active:text-primary-foreground dark:data-active:bg-primary dark:data-active:text-primary-foreground dark:data-active:border-transparent"
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {m.method_label}
                      {dirty && (
                        <span
                          aria-hidden
                          className="inline-block h-1.5 w-1.5 rounded-full bg-risk-med"
                          title="Unsaved changes on this tab"
                        />
                      )}
                    </span>
                  </TabsTrigger>
                );
              })}
            </TabsList>
            <HelpPopover title="Why these tabs?">
              <p>
                A tab appears for every collection method your tenant uses:
                either you&apos;ve scored at least one collection with that
                method, or you&apos;ve saved custom weights for it.
              </p>
              <p>
                Weights are stored per method, so a change on Card doesn&apos;t
                affect Debit Order scoring. Score a collection with a new
                method to see its tab appear, or use{" "}
                <span className="font-medium">Add method</span> to pre-configure
                weights before you start collecting with it.
              </p>
              <p>
                Card and Debit Order share the same underlying factor set,
                so they start with identical defaults. Tune them independently
                over time as your outcomes data shows which factors matter
                more per method.
              </p>
            </HelpPopover>
            {isAdmin && availableToAdd.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button variant="outline" size="sm" className="ml-auto">
                      <PlusIcon className="mr-1 h-4 w-4" />
                      Add method
                    </Button>
                  }
                />
                <DropdownMenuContent align="end">
                  <DropdownMenuGroup>
                    <DropdownMenuLabel>Add method tab</DropdownMenuLabel>
                    {availableToAdd.map((m) => (
                      <DropdownMenuItem
                        key={m}
                        disabled={addingMethod !== null}
                        onClick={() => handleAddMethod(m)}
                      >
                        {METHOD_CONFIG[m].label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuGroup>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {methods.map((entry) => {
            const draft = drafts[entry.collection_method];
            const total = methodTotal(draft);
            const valid = total === 100;
            const dirty = isDirty(draft);
            const saving = savingMethod === entry.collection_method;
            return (
              <TabsContent
                key={entry.collection_method}
                value={entry.collection_method}
                className="mt-4 space-y-6"
              >
                {entry.factors.map((f) => (
                  <WeightSliderRow
                    key={f.factor_name}
                    factorName={f.factor_name}
                    // API-provided label/description win; the client-side
                    // FACTOR_LABELS map is a fallback for factors added
                    // to the API before the frontend ships.
                    label={f.label}
                    description={f.description}
                    value={draft?.values[f.factor_name] ?? 0}
                    onChange={(v) => handleChange(entry.collection_method, f.factor_name, v)}
                    disabled={!isAdmin}
                  />
                ))}

                <div className="flex items-center justify-between border-t border-border pt-4">
                  <div className="flex items-center gap-2 text-sm">
                    {valid ? (
                      <CheckCircle2Icon className="h-4 w-4 text-risk-low" />
                    ) : (
                      <AlertCircleIcon className="h-4 w-4 text-risk-med" />
                    )}
                    <span className="text-muted-foreground">Total:</span>
                    <span
                      className={cn(
                        "font-mono tabular-nums font-medium",
                        !valid && "text-risk-med-fg",
                      )}
                    >
                      {total}%
                    </span>
                    <HelpPopover title="Why must weights sum to 100%?">
                      <p>
                        Each factor contributes a fraction of the final risk
                        score for this method. Weights are normalised, so the
                        sum has to be exactly 100% for the maths to work.
                      </p>
                      <p>
                        If a factor doesn&apos;t apply to a given row (e.g.
                        card health on a debit-order collection), the engine
                        skips it and re-normalises the remaining weights for
                        that score, but the base configuration here must
                        still sum to 100%.
                      </p>
                    </HelpPopover>
                  </div>
                  {isAdmin && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleReset(entry.collection_method)}
                        disabled={!dirty || saving}
                      >
                        Discard changes
                      </Button>
                      <Button
                        onClick={() => handleSave(entry.collection_method, entry)}
                        disabled={!valid || !dirty || saving}
                      >
                        {saving ? "Saving…" : `Save ${entry.method_label} weights`}
                      </Button>
                    </div>
                  )}
                </div>
              </TabsContent>
            );
          })}
        </Tabs>

        {/* When on a tab whose weights are still dirty, the persistent
            status line under the tab already tells the user their state;
            the summary is intentionally local per tab to avoid confusion
            about "what am I actually saving." */}
        {currentTotal !== 0 && !currentValid && !currentDirty && (
          <p className="text-xs text-risk-med-fg">
            Warning: {currentEntry.method_label} weights do not sum to 100%.
            Re-normalise before saving.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
