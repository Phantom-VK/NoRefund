import * as React from "react";
import { cn } from "@/lib/cn";

export type CardArt =
  | "contours"
  | "dots-flow"
  | "chevron"
  | "dots"
  | "stripes"
  | "dashes";

export interface CardProps extends Omit<React.ComponentProps<"div">, "children"> {
  /** Decorative corner illustration, clipped to the card by overflow-hidden.
   *  Purely visual — always aria-hidden. */
  art?: CardArt;
  /** CSS color for the illustration. Defaults to --primary. */
  artColor?: string;
  children: React.ReactNode;
}

export function Card({ art, artColor, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl bg-card text-card-foreground",
        className,
      )}
      {...props}
    >
      {art && (
        <div
          className={cn("card-art", `card-art--${art}`)}
          style={artColor ? ({ "--art-color": artColor } as React.CSSProperties) : undefined}
          aria-hidden="true"
        />
      )}
      <div className="relative z-10 flex h-full flex-col p-6">{children}</div>
    </div>
  );
}

export function CardTopRow({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex items-start justify-between", className)}>
      {children}
    </div>
  );
}

/** 58px colored icon square. Pass the icon and background color yourself —
 *  this only owns the shape. */
export function CardBadge({
  className,
  style,
  children,
}: {
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex size-[58px] shrink-0 items-center justify-center rounded-[3px] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]",
        className,
      )}
      style={style}
    >
      {children}
    </div>
  );
}

/** Category + title block. margin-top: auto pins it (and anything after it
 *  in the card) to the bottom of the card. */
export function CardBody({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={cn("mt-auto mb-4 max-w-[88%]", className)}>{children}</div>;
}
