"use client";

import { useEffect, useState } from "react";
import { CopyIcon, EyeIcon, EyeOffIcon, RefreshCwIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@/hooks/use-auth";
import { configApi } from "@/lib/api/config";

export function AlertsTab() {
  const { isAdmin } = useAuth();
  const { data, loading, error, refetch } = useApi(
    () => configApi.getAlertSettings(),
    [],
  );
  const [threshold, setThreshold] = useState(20);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [secretRevealed, setSecretRevealed] = useState(false);
  const [confirmingRotate, setConfirmingRotate] = useState(false);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    if (data) {
      setThreshold(data.high_risk_threshold * 100);
      setWebhookUrl(data.webhook_url ?? "");
      setSlackWebhookUrl(data.slack_webhook_url ?? "");
    }
  }, [data]);

  if (loading) return <LoadingSkeleton variant="rows" count={4} />;
  if (error) return <p className="text-sm text-muted-foreground">Failed to load alert settings: {error}</p>;
  if (!data) return null;

  const handleSaveThreshold = async () => {
    try {
      await configApi.updateAlertSettings({
        high_risk_threshold: threshold / 100,
      });
      toast.success("Threshold saved");
    } catch {
      toast.error("Failed to save threshold");
    }
  };

  const handleSaveWebhooks = async () => {
    try {
      await configApi.updateAlertSettings({
        webhook_url: webhookUrl || null,
        slack_webhook_url: slackWebhookUrl || null,
      });
      toast.success("Webhook URLs saved");
    } catch {
      toast.error("Failed to save webhook URLs");
    }
  };

  const handleCopySecret = async () => {
    await navigator.clipboard.writeText(data.webhook_secret);
    toast.success("Webhook secret copied to clipboard");
  };

  const handleRotate = async () => {
    setRotating(true);
    try {
      await configApi.rotateWebhookSecret();
      toast.success("Webhook secret rotated");
      setConfirmingRotate(false);
      setSecretRevealed(true);
      refetch();
    } catch {
      toast.error("Failed to rotate webhook secret");
    } finally {
      setRotating(false);
    }
  };

  // Mask all but the prefix and last 4 chars when hidden
  const masked = `${data.webhook_secret.slice(0, 6)}${"•".repeat(20)}${data.webhook_secret.slice(-4)}`;

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
            disabled={!isAdmin}
          />
          {isAdmin && (
            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={handleSaveThreshold}>
                Save threshold
              </Button>
            </div>
          )}
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
              disabled={!isAdmin}
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
              disabled={!isAdmin}
            />
          </div>
          {isAdmin && (
            <div className="flex justify-end">
              <Button size="sm" onClick={handleSaveWebhooks}>
                Save webhook URLs
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Webhook Signing Secret</CardTitle>
          <p className="text-sm text-muted-foreground">
            Each webhook delivery is signed with this secret using HMAC-SHA256
            in the <code className="rounded bg-muted px-1 py-0.5 text-xs">X-PayPredict-Signature</code>{" "}
            header. Use it on your receiver to verify the request came from PayPredict.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Secret</Label>
            <div className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto rounded-md border border-border bg-muted p-3 font-mono text-xs">
                {secretRevealed ? data.webhook_secret : masked}
              </code>
              <Button
                size="icon"
                variant="outline"
                onClick={() => setSecretRevealed((r) => !r)}
                title={secretRevealed ? "Hide secret" : "Reveal secret"}
              >
                {secretRevealed ? (
                  <EyeOffIcon className="h-4 w-4" />
                ) : (
                  <EyeIcon className="h-4 w-4" />
                )}
              </Button>
              <Button
                size="icon"
                variant="outline"
                onClick={handleCopySecret}
                title="Copy to clipboard"
              >
                <CopyIcon className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {!isAdmin ? (
            <p className="border-t border-border pt-4 text-xs text-muted-foreground">
              Only Admins can rotate the webhook secret.
            </p>
          ) : !confirmingRotate ? (
            <div className="flex items-center justify-between border-t border-border pt-4">
              <p className="text-xs text-muted-foreground">
                Rotating invalidates the current secret. In-flight webhooks signed
                with the old secret will fail signature verification.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="ml-4 gap-1.5"
                onClick={() => setConfirmingRotate(true)}
              >
                <RefreshCwIcon className="h-3.5 w-3.5" />
                Rotate secret
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-3 rounded-md border border-amber-500/30 bg-amber-50 p-3 dark:bg-amber-950/20">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Rotate the secret? Update your receiver immediately or webhook
                deliveries will fail signature verification.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmingRotate(false)}
                  disabled={rotating}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleRotate}
                  disabled={rotating}
                  className="bg-amber-500 text-white hover:bg-amber-600"
                >
                  {rotating ? "Rotating..." : "Rotate"}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
