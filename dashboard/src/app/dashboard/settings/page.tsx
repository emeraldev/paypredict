"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertsTab } from "@/components/settings/alerts-tab";
import { ApiKeysTab } from "@/components/settings/api-keys-tab";
import { TeamTab } from "@/components/settings/team-tab";
import { WeightsTab } from "@/components/settings/weights-tab";
import { useAuth } from "@/hooks/use-auth";

const VALID_TABS = ["weights", "api-keys", "alerts", "team"] as const;
type TabValue = (typeof VALID_TABS)[number];

function isValidTab(value: string | null): value is TabValue {
  return value !== null && (VALID_TABS as readonly string[]).includes(value);
}

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAdmin } = useAuth();
  const urlTab = searchParams.get("tab");
  // Team tab is Admin-only on the backend (require_admin); hide its
  // trigger and route non-admins requesting ?tab=team back to weights.
  const allowedTab = (t: TabValue): boolean => t !== "team" || isAdmin;
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
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="weights">Weights</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          {isAdmin && <TabsTrigger value="team">Team</TabsTrigger>}
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
      </Tabs>
    </div>
  );
}
