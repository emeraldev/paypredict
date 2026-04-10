import { Building, CreditCard, Smartphone } from "lucide-react";
import { cn } from "@/lib/utils";
import { getMethodConfig, type CollectionMethod } from "@/lib/utils/format-method";

interface MethodBadgeProps {
  method: CollectionMethod;
  className?: string;
}

const ICON_MAP = {
  CreditCard,
  Building,
  Smartphone,
} as const;

export function MethodBadge({ method, className }: MethodBadgeProps) {
  const config = getMethodConfig(method);
  const Icon = ICON_MAP[config.icon as keyof typeof ICON_MAP];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium",
        config.bg,
        config.color,
        config.border,
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {config.label}
    </span>
  );
}
