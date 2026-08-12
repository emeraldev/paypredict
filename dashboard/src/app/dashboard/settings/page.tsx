"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ActivityTable } from "@/components/settings/activity-table";
import { AlertsTab } from "@/components/settings/alerts-tab";
import { ApiKeysTab } from "@/components/settings/api-keys-tab";
import { TeamTab } from "@/components/settings/team-tab";
import { WeightsTab } from "@/components/settings/weights-tab";
import { PageHeader } from "@/components/shared/page-header";
import { useAuth } from "@/hooks/use-auth";

const VALID_TABS = ["weights", "api-keys", "alerts", "team", "activity"] as const;
type TabValue = (typeof VALID_TABS)[number];

function isValidTab(value: string | null): value is TabValue {
  return value !== null && (VALID_TABS as readonly string[]).includes(value);
}

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAdmin } = useAuth();
  const urlTab = searchParams.get("tab");
  // Team + Activity tabs are Admin-only on the backend; hide their
  // triggers and route non-admins requesting them back to weights.
  const allowedTab = (t: TabValue): boolean =>
    (t !== "team" && t !== "activity") || isAdmin;
  const activeTab: TabValue =
    isValidTab(urlTab) && allowedTab(urlTab) ? urlTab : "weights";

  const handleTabChange = (value: string) => {
    if (!isValidTab(value) || !allowedTab(value)) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", value);
    router.replace(`/dashboard/settings?${params.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Configure scoring weights, API keys, alerts, and team access"
      />

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList variant="line">
          <TabsTrigger value="weights">Weights</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          {isAdmin && <TabsTrigger value="team">Team</TabsTrigger>}
          {isAdmin && <TabsTrigger value="activity">Activity</TabsTrigger>}
        </TabsList>
        <TabsContent value="weights" className="mt-4">
          <WeightsTab />
        </TabsContent>
        <TabsContent value="api-keys" className="mt-4">
          <ApiKeysTab />
        </TabsContent>
        <TabsContent value="alerts" className="mt-4">
          <AlertsTab />
        </TabsContent>
        {isAdmin && (
          <TabsContent value="team" className="mt-4">
            <TeamTab />
          </TabsContent>
        )}
        {isAdmin && (
          <TabsContent value="activity" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Activity</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Every team, API-key, alert-config, webhook-secret, and
                  outcome change on this tenant. Compliance-facing.
                  Weight changes have their own trail on the Weights tab.
                </p>
              </CardHeader>
              <CardContent>
                <ActivityTable />
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
