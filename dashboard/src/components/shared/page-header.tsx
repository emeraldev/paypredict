import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  /** Optional element rendered inline next to the title. Typically a HelpPopover. */
  titleHelp?: ReactNode;
  /** Right-aligned slot: primary CTA, secondary controls, period selector, etc. */
  action?: ReactNode;
}

export function PageHeader({ title, subtitle, titleHelp, action }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 pb-2">
      <div className="min-w-0 space-y-1">
        <div className="flex items-center gap-1.5">
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            {title}
          </h1>
          {titleHelp}
        </div>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {action && (
        <div className="flex shrink-0 items-center gap-2">{action}</div>
      )}
    </div>
  );
}
