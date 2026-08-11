"use client";

import { TableCell, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import type { ApiKeyListItem } from "@/lib/api/types";
import { formatDate, formatRelativeTime } from "@/lib/utils/format-date";

interface ApiKeyRowProps {
  apiKey: ApiKeyListItem;
  /** Pass undefined to hide the Revoke button (e.g. for non-admin viewers). */
  onRevoke?: (id: string) => void;
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
              ? "inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-foreground"
              : "inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
          }
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${apiKey.is_active ? "bg-risk-low" : "bg-muted-foreground"}`}
          />
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
        {apiKey.is_active && onRevoke && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onRevoke(apiKey.id)}
            className="text-risk-high hover:bg-risk-high-bg hover:text-risk-high-fg"
          >
            Revoke
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
