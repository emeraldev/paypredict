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
  scoreId: string;
  collectionId: string;
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
  collectionId,
  onReported,
}: ReportOutcomeFormProps) {
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [failureReason, setFailureReason] = useState("");
  const [attemptedAt, setAttemptedAt] = useState(nowForInput);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!outcome) return;

    setSubmitting(true);
    try {
      await outcomesApi.create({
        score_id: scoreId,
        collection_id: collectionId,
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
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Report outcome
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          What happened when you attempted this collection?
        </p>
      </div>

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

      <Button type="submit" disabled={!outcome || submitting} className="w-full">
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
