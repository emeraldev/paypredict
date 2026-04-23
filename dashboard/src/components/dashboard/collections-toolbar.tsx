"use client";

import { DownloadIcon, SearchIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CollectionMethod } from "@/lib/utils/format-method";

export type DateRangeFilter = "today" | "3d" | "7d" | "14d" | "30d";

interface CollectionsToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  method: CollectionMethod | "ALL";
  onMethodChange: (value: CollectionMethod | "ALL") => void;
  dateRange: DateRangeFilter;
  onDateRangeChange: (value: DateRangeFilter) => void;
  onExport?: () => void;
}

export function CollectionsToolbar({
  search,
  onSearchChange,
  method,
  onMethodChange,
  dateRange,
  onDateRangeChange,
  onExport,
}: CollectionsToolbarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={dateRange}
          onValueChange={(v) => onDateRangeChange(v as DateRangeFilter)}
        >
          <SelectTrigger className="h-9 w-[140px] text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Today</SelectItem>
            <SelectItem value="3d">Next 3 days</SelectItem>
            <SelectItem value="7d">Next 7 days</SelectItem>
            <SelectItem value="14d">Next 14 days</SelectItem>
            <SelectItem value="30d">Next 30 days</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={method}
          onValueChange={(v) => onMethodChange(v as CollectionMethod | "ALL")}
        >
          <SelectTrigger className="h-9 w-[150px] text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All methods</SelectItem>
            <SelectItem value="CARD">Card</SelectItem>
            <SelectItem value="DEBIT_ORDER">Debit Order</SelectItem>
            <SelectItem value="MOBILE_MONEY">Mobile Money</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by customer or collection..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="h-9 w-64 pl-9 text-sm"
          />
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={onExport}>
          <DownloadIcon className="h-4 w-4" />
          Export
        </Button>
      </div>
    </div>
  );
}
