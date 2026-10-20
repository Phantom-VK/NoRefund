import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { VIEWS } from "@/lib/views";
import { isMac } from "@/hooks/useShortcuts";

export interface ShortcutsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShortcutsModal({ open, onOpenChange }: ShortcutsModalProps) {
  const modSymbol = isMac ? "⌘" : "Ctrl+";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Quick navigation and control shortcuts
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <div>
            <p className="type-micro text-muted-foreground mb-2">Navigation</p>
            <div className="space-y-1">
              {VIEWS.map((view) => (
                <div
                  key={view.id}
                  className="flex items-center justify-between py-1 text-sm"
                >
                  <div className="flex items-center gap-2.5 text-foreground">
                    <view.icon
                      size={16}
                      className="text-muted-foreground"
                      aria-hidden="true"
                    />
                    <span>{view.navLabel}</span>
                  </div>
                  <kbd className="inline-flex min-w-[28px] items-center justify-center rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground shadow-xs">
                    {modSymbol}{view.shortcut}
                  </kbd>
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-border pt-3">
            <p className="type-micro text-muted-foreground mb-2">General</p>
            <div className="space-y-1">
              <div className="flex items-center justify-between py-1 text-sm">
                <span className="text-foreground">Keyboard shortcuts</span>
                <kbd className="inline-flex min-w-[28px] items-center justify-center rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground shadow-xs">
                  ?
                </kbd>
              </div>
              <div className="flex items-center justify-between py-1 text-sm">
                <span className="text-foreground">Close surfaces / Cancel</span>
                <kbd className="inline-flex min-w-[28px] items-center justify-center rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground shadow-xs">
                  Esc
                </kbd>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
