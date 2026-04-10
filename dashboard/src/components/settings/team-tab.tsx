"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { mockTeamMembers } from "@/lib/mock-data";
import { formatRelativeTime } from "@/lib/utils/format-date";

const ROLE_STYLES: Record<string, string> = {
  ADMIN: "bg-red-950 text-red-400",
  MANAGER: "bg-blue-950 text-blue-400",
  VIEWER: "bg-zinc-800 text-zinc-400",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function TeamTab() {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base">Team Members</CardTitle>
          <p className="text-sm text-muted-foreground">
            People with access to this tenant&apos;s dashboard.
          </p>
        </div>
        <Button size="sm">Invite member</Button>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Member</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Last Login</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockTeamMembers.map((member) => (
              <TableRow key={member.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="text-xs">
                        {getInitials(member.name)}
                      </AvatarFallback>
                    </Avatar>
                    <span className="font-medium">{member.name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {member.email}
                </TableCell>
                <TableCell>
                  <span
                    className={cn(
                      "inline-flex rounded-md px-2 py-0.5 text-xs font-medium",
                      ROLE_STYLES[member.role],
                    )}
                  >
                    {member.role}
                  </span>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {member.last_login_at
                    ? formatRelativeTime(member.last_login_at)
                    : "Never"}
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm">
                    Manage
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
