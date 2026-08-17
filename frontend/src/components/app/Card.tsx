import * as React from "react";
import { cn } from "@/lib/cn";

export interface CardProps {
  className?: string;
  children: React.ReactNode;
  /** Renders a 3px --primary strip on the left edge. The card surface stays
   *  --card either way — GUI_REVIEW.md §4.1 documents what goes wrong when a
   *  "winning" state recolours the whole card instead of just accenting it. */
  accent?: boolean;
}

export function Card({ className, children, accent = false }: CardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border bg-card text-card-foreground",
        className,
      )}
    >
      {accent && (
        <div className="absolute inset-y-0 left-0 w-[3px] bg-primary" aria-hidden="true" />
      )}
      {children}
    </div>
  );
}
