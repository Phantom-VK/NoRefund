import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { Button as ShadcnButton } from "@/components/ui/button";
import { Spinner } from "./Spinner";
import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

// destructive already has a solid, non-hover rest state in the shadcn kit —
// mapping danger -> destructive fixes GUI_REVIEW.md §4.5 (the Tk danger
// button was indistinguishable from a neutral one until hovered).
const VARIANT_MAP: Record<
  ButtonVariant,
  "default" | "secondary" | "ghost" | "destructive"
> = {
  primary: "default",
  secondary: "secondary",
  ghost: "ghost",
  danger: "destructive",
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: LucideIcon;
  loading?: boolean;
}

export function Button({
  variant = "secondary",
  icon: Icon,
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <ShadcnButton
      variant={VARIANT_MAP[variant]}
      className={cn("pressable", className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <Spinner size={16} />
      ) : Icon ? (
        <Icon size={16} aria-hidden="true" />
      ) : null}
      {children}
    </ShadcnButton>
  );
}
