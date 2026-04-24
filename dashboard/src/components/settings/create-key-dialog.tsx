"use client";

import { CopyIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { configApi } from "@/lib/api/config";

interface CreateKeyDialogProps {
  onCreated?: () => void;
}

export function CreateKeyDialog({ onCreated }: CreateKeyDialogProps) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!label.trim()) {
      toast.error("Enter a label for the key");
      return;
    }
    setCreating(true);
    try {
      const res = await configApi.createApiKey(label.trim());
      setGeneratedKey(res.key);
    } catch {
      toast.error("Failed to create API key");
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!generatedKey) return;
    await navigator.clipboard.writeText(generatedKey);
    toast.success("Key copied to clipboard");
  };

  const handleClose = () => {
    const wasCreated = generatedKey !== null;
    setOpen(false);
    setTimeout(() => {
      setLabel("");
      setGeneratedKey(null);
    }, 200);
    if (wasCreated && onCreated) {
      onCreated();
    }
  };

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        Create new key
      </Button>
      <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : handleClose())}>
        <DialogContent>
        <DialogHeader>
          <DialogTitle>Create API Key</DialogTitle>
          <DialogDescription>
            {generatedKey
              ? "Copy your key now — it won't be shown again."
              : "Give your key a descriptive label."}
          </DialogDescription>
        </DialogHeader>

        {!generatedKey ? (
          <div className="space-y-2 py-4">
            <Label htmlFor="label">Label</Label>
            <Input
              id="label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Production server"
            />
          </div>
        ) : (
          <div className="space-y-2 py-4">
            <Label>Your API key</Label>
            <div className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto rounded-md border border-border bg-muted p-3 text-xs font-mono">
                {generatedKey}
              </code>
              <Button size="icon" variant="outline" onClick={handleCopy}>
                <CopyIcon className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-amber-400">
              Store this key securely. You will not be able to see it again.
            </p>
          </div>
        )}

        <DialogFooter>
          {!generatedKey ? (
            <Button onClick={handleCreate} disabled={creating}>
              {creating ? "Creating..." : "Create key"}
            </Button>
          ) : (
            <Button onClick={handleClose}>Done</Button>
          )}
        </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
