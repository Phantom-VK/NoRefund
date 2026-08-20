import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Button } from "./Button";
import { Spinner } from "./Spinner";

export interface ProcessingDialogProps {
  open: boolean;
  title: string;
  description?: string;
  cancelling: boolean;
  onCancel: () => void;
}

/** Blocks the rest of the UI while a job is running. Cancel (the button, or
 *  Escape) always dismisses the dialog immediately, whether or not the
 *  underlying job can actually be interrupted -- some jobs (a huge single
 *  file, a text-only Compare with no cancel support at all) can't stop
 *  mid-call, and a lost completion event must never leave this dialog as
 *  the only thing standing between the user and the rest of the app.
 *  `onCancel` still fires so the caller's own cancel/cancelling state
 *  updates normally; this component just stops being the app's only door
 *  once the user has asked to leave. */
export function ProcessingDialog({ open, title, description, cancelling, onCancel }: ProcessingDialogProps) {
  const [dismissed, setDismissed] = useState(false);

  // A fresh run (open flips false -> true) always gets its own dialog.
  useEffect(() => {
    if (open) setDismissed(false);
  }, [open]);

  function cancelAndDismiss() {
    setDismissed(true);
    onCancel();
  }

  return (
    <Dialog open={open && !dismissed}>
      <DialogContent
        showCloseButton={false}
        className="max-w-sm"
        onEscapeKeyDown={(e) => {
          e.preventDefault();
          cancelAndDismiss();
        }}
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
      >
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <Spinner size={32} className="text-primary" />
          <DialogTitle className="type-title">{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
          <Button
            type="button"
            variant="danger"
            loading={cancelling}
            disabled={cancelling}
            onClick={cancelAndDismiss}
            className="mt-2"
          >
            {cancelling ? "Cancelling…" : "Cancel"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
