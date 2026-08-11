"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  /** Label on the confirm button. Defaults to "Confirm". */
  confirmLabel?: string;
  /** Label on the cancel button. Defaults to "Cancel". */
  cancelLabel?: string;
  /** Visual weight of the confirm action. Use "destructive" for
   *  irreversible operations (delete, remove, revoke, rotate). */
  variant?: "default" | "destructive";
  /**
   * Called when the user clicks confirm. Component awaits the returned
   * promise and closes on success. If the promise rejects, the dialog
   * stays open (assumes the caller shows a toast inside the catch).
   */
  onConfirm: () => Promise<void> | void;
}

/**
 * Standardised in-app confirmation. Replaces `window.confirm()` for
 * every user-facing destructive/irreversible action so we own the
 * chrome, styling, and messaging instead of getting the browser's
 * unbranded native dialog.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  const [confirming, setConfirming] = useState(false);

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      // Caller handles user-facing error (toast). We just release the
      // loading state and leave the dialog open so they can retry.
    } finally {
      setConfirming(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={confirming}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={variant}
            onClick={handleConfirm}
            disabled={confirming}
          >
            {confirming ? "Working..." : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
