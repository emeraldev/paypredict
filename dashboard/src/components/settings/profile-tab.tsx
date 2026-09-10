"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

// Mirrors api/app/schemas/_validators.py `validate_password`. Client-side
// echo is UX only — the backend re-validates and 422s regardless.
const MIN_LENGTH = 12;
const MAX_LENGTH = 72;

function classesPresent(pw: string): number {
  let n = 0;
  if (/[A-Z]/.test(pw)) n++;
  if (/[a-z]/.test(pw)) n++;
  if (/\d/.test(pw)) n++;
  if (/[^A-Za-z0-9]/.test(pw)) n++;
  return n;
}

function localPolicyError(pw: string): string | null {
  if (pw.length < MIN_LENGTH) return `At least ${MIN_LENGTH} characters.`;
  if (pw.length > MAX_LENGTH) return `At most ${MAX_LENGTH} characters.`;
  if (classesPresent(pw) < 3)
    return "Include at least 3 of: uppercase, lowercase, digit, symbol.";
  return null;
}

export function ProfileTab() {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const nextError = next ? localPolicyError(next) : null;
  const confirmError =
    confirm && next && confirm !== next ? "Passwords don't match." : null;
  const canSubmit =
    !!current && !!next && !!confirm && !nextError && !confirmError && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await authApi.changePassword({
        current_password: current,
        new_password: next,
      });
      toast.success("Password updated. Other sessions have been signed out.");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error("Could not update password. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
          <p className="text-sm text-muted-foreground">
            Signed in as {user?.email}.
          </p>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change password</CardTitle>
          <p className="text-sm text-muted-foreground">
            Rotating your password signs you out of every other session
            and returns you here with a fresh token. Requires your
            current password.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
            <div className="space-y-2">
              <Label htmlFor="current-password">Current password</Label>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-password">New password</Label>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                required
                aria-invalid={!!nextError}
                aria-describedby="new-password-help"
              />
              <p
                id="new-password-help"
                className={
                  nextError
                    ? "text-xs text-destructive"
                    : "text-xs text-muted-foreground"
                }
              >
                {nextError ??
                  `At least ${MIN_LENGTH} characters, mix of at least 3 of: uppercase, lowercase, digit, symbol.`}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                aria-invalid={!!confirmError}
              />
              {confirmError && (
                <p className="text-xs text-destructive">{confirmError}</p>
              )}
            </div>

            <div className="pt-2">
              <Button type="submit" disabled={!canSubmit}>
                {submitting ? "Updating..." : "Update password"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
