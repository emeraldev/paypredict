"use client";

import { CheckCircle2Icon, XCircleIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { outcomesApi } from "@/lib/api/outcomes";
import { cn } from "@/lib/utils";

interface ReportOutcomeFormProps {
  /** Pre-filled when the form is opened from a known score (e.g. the
   *  risk-detail drawer). When omitted, the backend auto-links the outcome
   *  by collection_id. */
  scoreId?: string;
  /** Pre-filled when known. When omitted, the form renders an input so the
   *  clerk can type the collection reference themselves. */
  collectionId?: string;
  /** Render mode. "section" renders bare for embedding in the drawer.
   *  "standalone" hides the "Report outcome" header (the dialog title
   *  carries that), and shows the collection_id input when needed. */
  variant?: "section" | "standalone";
  onReported: () => void;
}

type Outcome = "SUCCESS" | "FAILED" | null;

// Datetime-local format expected by the input: YYYY-MM-DDTHH:MM
function nowForInput(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function ReportOutcomeForm({
  scoreId,
  collectionId: collectionIdProp,
  variant = "section",
  onReported,
}: ReportOutcomeFormProps) {
  const [collectionIdInput, setCollectionIdInput] = useState("");
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [failureReason, setFailureReason] = useState("");
  const [attemptedAt, setAttemptedAt] = useState(nowForInput);
  const [submitting, setSubmitting] = useState(false);

  // Use the prop when provided; otherwise the user-input value.
  const effectiveCollectionId =
    collectionIdProp ?? collectionIdInput.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!outcome || !effectiveCollectionId) return;

    setSubmitting(true);
    try {
      await outcomesApi.create({
        score_id: scoreId,
        collection_id: effectiveCollectionId,
        outcome,
        failure_reason:
          outcome === "FAILED" && failureReason.trim()
            ? failureReason.trim()
            : undefined,
        // datetime-local has no timezone — treat as local time, send ISO.
        attempted_at: new Date(attemptedAt).toISOString(),
      });
      toast.success("Outcome recorded");
      onReported();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to record outcome");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {variant === "section" && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Report outcome
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            What happened when you attempted this collection?
          </p>
        </div>
      )}

      {/* collection_id input — only shown when not pre-filled */}
      {collectionIdProp === undefined && (
        <div>
          <Label htmlFor="collection_id" className="text-xs">
            Collection reference
          </Label>
          <Input
            id="collection_id"
            value={collectionIdInput}
            onChange={(e) => setCollectionIdInput(e.target.value)}
            placeholder="inst_001"
            required
            className="mt-1"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Your reference for the collection that was attempted. We&apos;ll
            link this outcome to the matching score automatically.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <OutcomeButton
          label="Succeeded"
          icon={<CheckCircle2Icon className="h-4 w-4" />}
          selected={outcome === "SUCCESS"}
          tone="emerald"
          onClick={() => setOutcome("SUCCESS")}
        />
        <OutcomeButton
          label="Failed"
          icon={<XCircleIcon className="h-4 w-4" />}
          selected={outcome === "FAILED"}
          tone="red"
          onClick={() => setOutcome("FAILED")}
        />
      </div>

      {outcome === "FAILED" && (
        <div>
          <Label htmlFor="failure_reason" className="text-xs">
            Reason (optional)
          </Label>
          <Input
            id="failure_reason"
            value={failureReason}
            onChange={(e) => setFailureReason(e.target.value)}
            placeholder="insufficient_funds, account_closed, ..."
            className="mt-1"
          />
        </div>
      )}

      <div>
        <Label htmlFor="attempted_at" className="text-xs">
          Attempted at
        </Label>
        <Input
          id="attempted_at"
          type="datetime-local"
          value={attemptedAt}
          onChange={(e) => setAttemptedAt(e.target.value)}
          required
          className="mt-1"
        />
      </div>

      <Button
        type="submit"
        disabled={!outcome || !effectiveCollectionId || submitting}
        className="w-full"
      >
        {submitting ? "Recording…" : "Record outcome"}
      </Button>
    </form>
  );
}

function OutcomeButton({
  label,
  icon,
  selected,
  tone,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  selected: boolean;
  tone: "emerald" | "red";
  onClick: () => void;
}) {
  const baseClass =
    "flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors";
  const selectedClass =
    tone === "emerald"
      ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-400"
      : "border-red-500/60 bg-red-500/10 text-red-400";
  const idleClass =
    "border-border bg-card text-muted-foreground hover:bg-accent/50";
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(baseClass, selected ? selectedClass : idleClass)}
    >
      {icon}
      {label}
    </button>
  );
}
