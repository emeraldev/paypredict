"use client";

import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { configApi } from "@/lib/api/config";
import { ApiKeyRow } from "./api-key-row";
import { CreateKeyDialog } from "./create-key-dialog";

export function ApiKeysTab() {
  const { data, loading, error, refetch } = useApi(() => configApi.getApiKeys(), []);

  const handleRevoke = async (id: string) => {
    try {
      await configApi.revokeApiKey(id);
      toast.success("API key revoked");
      refetch();
    } catch {
      toast.error("Failed to revoke key");
    }
  };

  if (loading) return <LoadingSkeleton variant="rows" count={3} />;
  if (error) return <p className="text-sm text-muted-foreground">Failed to load API keys: {error}</p>;

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
            {(data?.items ?? []).map((key) => (
              <ApiKeyRow key={key.id} apiKey={key} onRevoke={handleRevoke} />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
