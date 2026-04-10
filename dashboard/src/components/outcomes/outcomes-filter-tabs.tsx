"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { OutcomeFilter } from "@/lib/api/types";

interface OutcomesFilterTabsProps {
  value: OutcomeFilter;
  onChange: (value: OutcomeFilter) => void;
}

export function OutcomesFilterTabs({ value, onChange }: OutcomesFilterTabsProps) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as OutcomeFilter)}>
      <TabsList>
        <TabsTrigger value="ALL">All</TabsTrigger>
        <TabsTrigger value="MATCHED">Matched</TabsTrigger>
        <TabsTrigger value="MISMATCHED">Mismatched</TabsTrigger>
        <TabsTrigger value="PENDING">Pending</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
