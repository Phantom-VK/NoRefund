import * as React from "react";
import { cn } from "@/lib/cn";

export interface SectionLabelProps {
  children: React.ReactNode;
  className?: string;
}

export function SectionLabel({ children, className }: SectionLabelProps) {
  return (
    <div className={cn("type-micro text-muted-foreground", className)}>
      {children}
    </div>
  );
}
