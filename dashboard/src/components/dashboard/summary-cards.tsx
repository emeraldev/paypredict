"use client";

import type { Collection } from "@/lib/api/types";
import type { RiskLevel } from "@/lib/utils/format-risk";
import { SummaryCard } from "./summary-card";

interface SummaryCardsProps {
  collections: Collection[];
  activeFilter: RiskLevel | null;
  onFilterChange: (filter: RiskLevel | null) => void;
}

export function SummaryCards({
  collections,
  activeFilter,
  onFilterChange,
}: SummaryCardsProps) {
  const total = collections.length;
  const high = collections.filter((c) => c.risk_level === "HIGH").length;
  const medium = collections.filter((c) => c.risk_level === "MEDIUM").length;
  const low = collections.filter((c) => c.risk_level === "LOW").length;

  const toggleFilter = (level: RiskLevel) => {
    onFilterChange(activeFilter === level ? null : level);
  };

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <SummaryCard
        title="Upcoming Collections"
        value={total}
        subtitle="In the next 30 days"
        accentColor="border-l-zinc-500"
        active={activeFilter === null}
        onClick={() => onFilterChange(null)}
      />
      <SummaryCard
        title="High Risk"
        value={high}
        subtitle={`${total > 0 ? Math.round((high / total) * 100) : 0}% of total`}
        accentColor="border-l-red-500"
        active={activeFilter === "HIGH"}
        onClick={() => toggleFilter("HIGH")}
      />
      <SummaryCard
        title="Medium Risk"
        value={medium}
        subtitle={`${total > 0 ? Math.round((medium / total) * 100) : 0}% of total`}
        accentColor="border-l-amber-500"
        active={activeFilter === "MEDIUM"}
        onClick={() => toggleFilter("MEDIUM")}
      />
      <SummaryCard
        title="Low Risk"
        value={low}
        subtitle={`${total > 0 ? Math.round((low / total) * 100) : 0}% of total`}
        accentColor="border-l-emerald-500"
        active={activeFilter === "LOW"}
        onClick={() => toggleFilter("LOW")}
      />
    </div>
  );
}
