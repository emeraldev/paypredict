"use client";

import { TableCell, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import type { ApiKeyListItem } from "@/lib/api/types";
import { formatDate, formatRelativeTime } from "@/lib/utils/format-date";

interface ApiKeyRowProps {
  apiKey: ApiKeyListItem;
  onRevoke: (id: string) => void;
}

export function ApiKeyRow({ apiKey, onRevoke }: ApiKeyRowProps) {
  return (
    <TableRow>
      <TableCell className="font-medium">{apiKey.label}</TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">
        {apiKey.prefix}•••••••••
      </TableCell>
      <TableCell>
        <span
          className={
            apiKey.is_active
              ? "inline-flex rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400"
              : "inline-flex rounded-md border border-zinc-500/30 bg-zinc-500/10 px-2 py-0.5 text-xs font-medium text-zinc-400"
          }
        >
          {apiKey.is_active ? "Active" : "Revoked"}
        </span>
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">
        {apiKey.last_used_at ? formatRelativeTime(apiKey.last_used_at) : "Never"}
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">
        {formatDate(apiKey.created_at)}
      </TableCell>
      <TableCell className="text-right">
        {apiKey.is_active && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onRevoke(apiKey.id)}
            className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
          >
            Revoke
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
