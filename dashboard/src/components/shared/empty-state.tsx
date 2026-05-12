import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  size = "md",
}: EmptyStateProps) {
  const padY = size === "sm" ? "py-10" : size === "lg" ? "py-24" : "py-16";
  const iconBox =
    size === "sm" ? "h-12 w-12" : size === "lg" ? "h-20 w-20" : "h-16 w-16";
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 text-center",
        padY,
        className,
      )}
    >
      {icon && (
        <div
          className={cn(
            "flex items-center justify-center rounded-full bg-muted/60 text-muted-foreground ring-1 ring-border/60",
            iconBox,
          )}
        >
          {icon}
        </div>
      )}
      <div className="space-y-1.5">
        <h3 className="text-base font-medium text-foreground">{title}</h3>
        {description && (
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
