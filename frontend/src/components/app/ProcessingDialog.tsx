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

/** Blocks the rest of the UI while a job is running -- no close button, and
 *  escape/outside-click are swallowed so the only way out is Cancel. */
export function ProcessingDialog({ open, title, description, cancelling, onCancel }: ProcessingDialogProps) {
  return (
    <Dialog open={open}>
      <DialogContent
        showCloseButton={false}
        className="max-w-sm"
        onEscapeKeyDown={(e) => e.preventDefault()}
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
            onClick={onCancel}
            className="mt-2"
          >
            {cancelling ? "Cancelling…" : "Cancel"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
