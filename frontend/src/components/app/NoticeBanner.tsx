import { TriangleAlert, X } from "lucide-react";
import { Button } from "@/components/app/Button";

export interface NoticeBannerProps {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss: () => void;
}

export function NoticeBanner({
  message,
  actionLabel,
  onAction,
  onDismiss,
}: NoticeBannerProps) {
  return (
    <div
      role="status"
      className="flex shrink-0 items-center gap-3 bg-warning px-4 py-2 text-warning-foreground"
    >
      <TriangleAlert size={16} className="shrink-0" aria-hidden="true" />
      <p className="type-small flex-1">{message}</p>
      {actionLabel && onAction && (
        <Button
          variant="ghost"
          className="h-7 px-2 text-warning-foreground hover:bg-black/10"
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      )}
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        className="pressable rounded-md p-1 hover:bg-black/10"
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}
