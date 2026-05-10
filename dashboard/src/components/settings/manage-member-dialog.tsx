"use client";

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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { configApi } from "@/lib/api/config";
import type { TeamMember } from "@/lib/api/types";

interface ManageMemberDialogProps {
  member: TeamMember;
  onUpdated: () => void;
}

export function ManageMemberDialog({ member, onUpdated }: ManageMemberDialogProps) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<string>(member.role);
  const [submitting, setSubmitting] = useState(false);
  const [confirmingRemove, setConfirmingRemove] = useState(false);

  const handleClose = () => {
    setOpen(false);
    setTimeout(() => {
      setRole(member.role);
      setConfirmingRemove(false);
    }, 200);
  };

  const handleSaveRole = async () => {
    if (role === member.role) {
      handleClose();
      return;
    }
    setSubmitting(true);
    try {
      await configApi.updateMemberRole(member.id, role);
      toast.success("Role updated");
      handleClose();
      onUpdated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update role");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async () => {
    setSubmitting(true);
    try {
      await configApi.removeMember(member.id);
      toast.success(`${member.name} removed from team`);
      handleClose();
      onUpdated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove member");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        Manage
      </Button>
      <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : handleClose())}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Manage {member.name}</DialogTitle>
            <DialogDescription>
              {member.email}
            </DialogDescription>
          </DialogHeader>

          {!confirmingRemove ? (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={role} onValueChange={(v) => v && setRole(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ADMIN">Admin</SelectItem>
                    <SelectItem value="MANAGER">Manager</SelectItem>
                    <SelectItem value="VIEWER">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="border-t border-border pt-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmingRemove(true)}
                  className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
                >
                  Remove from team
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2 py-4">
              <p className="text-sm text-foreground">
                Remove <span className="font-semibold">{member.name}</span> from the team?
              </p>
              <p className="text-xs text-muted-foreground">
                They will lose access to the dashboard immediately. This cannot be undone.
              </p>
            </div>
          )}

          <DialogFooter>
            {!confirmingRemove ? (
              <>
                <Button variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button onClick={handleSaveRole} disabled={submitting}>
                  {submitting ? "Saving..." : "Save"}
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() => setConfirmingRemove(false)}
                  disabled={submitting}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleRemove}
                  disabled={submitting}
                  className="bg-red-500 text-white hover:bg-red-600"
                >
                  {submitting ? "Removing..." : "Remove"}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
