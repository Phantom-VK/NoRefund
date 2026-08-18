import * as React from "react";
import type { LucideIcon } from "lucide-react";

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center text-muted-foreground">
      <Icon size={32} className="opacity-60" aria-hidden="true" />
      <p className="type-title text-foreground">{title}</p>
      {description && <p className="type-body max-w-sm">{description}</p>}
      {action}
    </div>
  );
}
