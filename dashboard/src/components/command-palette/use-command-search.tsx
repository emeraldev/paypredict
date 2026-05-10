"use client";

import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2Icon,
  CreditCardIcon,
  FlaskConicalIcon,
} from "lucide-react";

import { backtestApi } from "@/lib/api/backtest";
import { outcomesApi } from "@/lib/api/outcomes";
import { scoresApi } from "@/lib/api/scores";

import type { CommandItem } from "./command-types";

const DEBOUNCE_MS = 200;
const MAX_PER_GROUP = 5;

interface UseCommandSearchResult {
  results: CommandItem[];
  loading: boolean;
}

/** Debounced parallel search across scores, outcomes, and backtests.
 * Returns combined results in a stable group order. */
export function useCommandSearch(query: string): UseCommandSearchResult {
  const [results, setResults] = useState<CommandItem[]>([]);
  const [loading, setLoading] = useState(false);
  const fetchId = useRef(0);

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setLoading(false);
      return;
    }

    const id = ++fetchId.current;
    setLoading(true);

    const handle = setTimeout(async () => {
      try {
        const [scoresRes, outcomesRes, backtestsRes] = await Promise.all([
          scoresApi.list({ search: trimmed, page_size: MAX_PER_GROUP }).catch(() => null),
          outcomesApi.list({ search: trimmed, page_size: MAX_PER_GROUP }).catch(() => null),
          backtestApi.list({ search: trimmed }).catch(() => null),
        ]);

        // Stale guard — newer call took over
        if (id !== fetchId.current) return;

        const items: CommandItem[] = [];

        if (scoresRes?.items?.length) {
          for (const s of scoresRes.items.slice(0, MAX_PER_GROUP)) {
            items.push({
              id: `score-${s.score_id}`,
              label: s.external_customer_id,
              hint: `${s.external_collection_id} · ${s.risk_level} (${(s.score * 100).toFixed(0)})`,
              icon: CreditCardIcon,
              group: "Collections",
              href: `/dashboard?search=${encodeURIComponent(trimmed)}`,
            });
          }
        }

        if (outcomesRes?.items?.length) {
          for (const o of outcomesRes.items.slice(0, MAX_PER_GROUP)) {
            items.push({
              id: `outcome-${o.outcome_id}`,
              label: o.external_collection_id,
              hint: `${o.outcome}${o.failure_reason ? ` · ${o.failure_reason}` : ""}`,
              icon: CheckCircle2Icon,
              group: "Outcomes",
              href: "/dashboard/outcomes",
            });
          }
        }

        if (backtestsRes?.items?.length) {
          for (const b of backtestsRes.items.slice(0, MAX_PER_GROUP)) {
            items.push({
              id: `backtest-${b.backtest_id}`,
              label: b.name ?? "Untitled backtest",
              hint: `${b.total_collections} collections${
                b.overall_accuracy != null
                  ? ` · ${Math.round(b.overall_accuracy * 100)}% accuracy`
                  : ""
              }`,
              icon: FlaskConicalIcon,
              group: "Backtests",
              href: "/dashboard/backtest",
            });
          }
        }

        setResults(items);
      } finally {
        if (id === fetchId.current) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(handle);
  }, [query]);

  return { results, loading };
}
