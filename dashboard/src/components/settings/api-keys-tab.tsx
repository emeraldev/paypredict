"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ApiKey } from "@/lib/api/types";
import { mockApiKeys } from "@/lib/mock-data";
import { ApiKeyRow } from "./api-key-row";
import { CreateKeyDialog } from "./create-key-dialog";

export function ApiKeysTab() {
  const [keys, setKeys] = useState<ApiKey[]>(mockApiKeys);

  const handleRevoke = (id: string) => {
    setKeys((prev) => prev.map((k) => (k.id === id ? { ...k, is_active: false } : k)));
    toast.success("API key revoked");
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base">API Keys</CardTitle>
          <p className="text-sm text-muted-foreground">
            Manage keys used to authenticate against the PayPredict API.
          </p>
        </div>
        <CreateKeyDialog />
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Label</TableHead>
              <TableHead>Key</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {keys.map((key) => (
              <ApiKeyRow key={key.id} apiKey={key} onRevoke={handleRevoke} />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
