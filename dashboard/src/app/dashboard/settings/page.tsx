"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertsTab } from "@/components/settings/alerts-tab";
import { ApiKeysTab } from "@/components/settings/api-keys-tab";
import { TeamTab } from "@/components/settings/team-tab";
import { WeightsTab } from "@/components/settings/weights-tab";
import { PageHeader } from "@/components/shared/page-header";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Factor weights, API keys, alerts, and team management"
      />

      <Tabs defaultValue="weights">
        <TabsList>
          <TabsTrigger value="weights">Weights</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
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
        <TabsContent value="team" className="mt-4">
          <TeamTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
