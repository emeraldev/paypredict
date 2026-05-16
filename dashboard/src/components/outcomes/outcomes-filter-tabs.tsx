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
        <TabsTrigger value="ALL" title="Every reported outcome, regardless of whether the prediction was right">
          All
        </TabsTrigger>
        <TabsTrigger
          value="MATCHED"
          title="Outcomes where we got it right — HIGH/MEDIUM risk that actually failed, or LOW risk that succeeded"
        >
          Matched predictions
        </TabsTrigger>
        <TabsTrigger
          value="MISMATCHED"
          title="Outcomes where the model missed — HIGH/MEDIUM risk that succeeded, or LOW risk that failed"
        >
          Mismatched predictions
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
