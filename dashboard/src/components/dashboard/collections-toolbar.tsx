"use client";

import { SearchIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CollectionMethod } from "@/lib/utils/format-method";

interface CollectionsToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  method: CollectionMethod | "ALL";
  onMethodChange: (value: CollectionMethod | "ALL") => void;
}

export function CollectionsToolbar({
  search,
  onSearchChange,
  method,
  onMethodChange,
}: CollectionsToolbarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative flex-1 max-w-sm">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by customer or collection ID..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9 focus-visible:ring-emerald-500/30 focus-visible:border-emerald-500/60"
        />
      </div>
      <Select
        value={method}
        onValueChange={(v) => onMethodChange(v as CollectionMethod | "ALL")}
      >
        <SelectTrigger className="w-full sm:w-48 focus-visible:ring-emerald-500/30">
          <SelectValue placeholder="All methods" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All methods</SelectItem>
          <SelectItem value="CARD">Card</SelectItem>
          <SelectItem value="DEBIT_ORDER">Debit Order</SelectItem>
          <SelectItem value="MOBILE_MONEY">Mobile Money</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
