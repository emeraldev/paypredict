import { PageHeader } from "@/components/shared/page-header";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Factor weights, API keys, alerts, and team"
      />
      <p className="text-sm text-muted-foreground">Coming in Step 7.</p>
    </div>
  );
}
