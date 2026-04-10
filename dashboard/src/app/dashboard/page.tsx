import { PageHeader } from "@/components/shared/page-header";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Risk-ranked upcoming collections"
      />
      <p className="text-sm text-muted-foreground">Coming in Step 4.</p>
    </div>
  );
}
