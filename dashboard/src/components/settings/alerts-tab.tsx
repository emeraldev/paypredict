"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { mockAlertSettings } from "@/lib/mock-data";

export function AlertsTab() {
  const [threshold, setThreshold] = useState(mockAlertSettings.alert_threshold * 100);
  const [webhookUrl, setWebhookUrl] = useState(mockAlertSettings.webhook_url ?? "");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState(
    mockAlertSettings.slack_webhook_url ?? "",
  );

  const handleSave = () => {
    toast.success("Alert settings saved");
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
