"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { configApi } from "@/lib/api/config";

export function AlertsTab() {
  const { data, loading, error } = useApi(() => configApi.getAlertSettings(), []);
  const [threshold, setThreshold] = useState(20);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");

  useEffect(() => {
    if (data) {
      setThreshold(data.high_risk_threshold * 100);
      setWebhookUrl(data.webhook_url ?? "");
      setSlackWebhookUrl(data.slack_webhook_url ?? "");
    }
  }, [data]);

  if (loading) return <LoadingSkeleton variant="rows" count={4} />;
  if (error) return <p className="text-sm text-muted-foreground">Failed to load alert settings: {error}</p>;

  const handleSave = async () => {
    try {
      await configApi.updateAlertSettings({
        high_risk_threshold: threshold / 100,
        webhook_url: webhookUrl || null,
        slack_webhook_url: slackWebhookUrl || null,
      });
      toast.success("Alert settings saved");
    } catch {
      toast.error("Failed to save alert settings");
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alert Threshold</CardTitle>
          <p className="text-sm text-muted-foreground">
            Trigger alerts when more than this percentage of a batch is high risk.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>High-risk batch threshold</Label>
            <span className="font-mono tabular-nums">{Math.round(threshold)}%</span>
          </div>
          <Slider
            value={[threshold]}
            onValueChange={(v) => {
              const value = Array.isArray(v) ? v[0] : v;
              setThreshold(value);
            }}
            min={5}
            max={50}
            step={1}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Webhook Delivery</CardTitle>
          <p className="text-sm text-muted-foreground">
            Receive alerts via HTTP webhook or Slack incoming webhook.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhook">HTTP Webhook URL</Label>
            <Input
              id="webhook"
              type="url"
              placeholder="https://api.yoursite.com/paypredict-webhook"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="slack">Slack Webhook URL</Label>
            <Input
              id="slack"
              type="url"
              placeholder="https://hooks.slack.com/services/..."
              value={slackWebhookUrl}
              onChange={(e) => setSlackWebhookUrl(e.target.value)}
            />
          </div>
          <div className="flex justify-end">
            <Button size="sm" onClick={handleSave}>
              Save alert settings
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
