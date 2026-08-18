import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { bridge, BridgeError } from "@/lib/bridge";
import { parseIntSafe } from "@/lib/format";
import type { Settings } from "@/lib/types";

const CURRENCIES = ["USD", "EUR", "GBP", "INR"];

export interface SettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  settings: Settings;
  onSave: (patch: Partial<Settings>) => Promise<void>;
}

export function SettingsModal({
  open,
  onOpenChange,
  settings,
  onSave,
}: SettingsModalProps) {
  const [outputTokensRaw, setOutputTokensRaw] = useState(
    String(settings.default_output_tokens),
  );
  const [currency, setCurrency] = useState(settings.currency);
  const [chunkWarnings, setChunkWarnings] = useState(settings.show_chunk_warnings);
  const [tokenInput, setTokenInput] = useState("");
  const [keyringOk, setKeyringOk] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The gear button lives in Header, a different subtree from this Dialog,
  // so Radix's default onCloseAutoFocus (which only knows about a
  // <DialogTrigger> inside the same tree) has nothing to restore focus to.
  // Capture whatever was focused right as we open -- that's the gear
  // button for a real click -- and restore it ourselves on close.
  const openerRef = useRef<HTMLElement | null>(null);

  // Re-seed the draft from the latest known-good settings every time the
  // modal opens, and load the two secrets-only fields that live outside
  // the Settings dataclass.
  useEffect(() => {
    if (!open) return;
    openerRef.current = document.activeElement as HTMLElement | null;
    setOutputTokensRaw(String(settings.default_output_tokens));
    setCurrency(settings.currency);
    setChunkWarnings(settings.show_chunk_warnings);
    setTokenInput("");
    setError(null);
    Promise.all([bridge.keyringAvailable(), bridge.hasHfToken()]).then(
      ([available, has]) => {
        setKeyringOk(available);
        setHasToken(has);
      },
    );
    // settings is intentionally excluded: re-running this on every settings
    // change (e.g. the header's theme toggle while the modal is open) would
    // clobber whatever the user is mid-typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const outputTokens = parseIntSafe(outputTokensRaw);
  const outputTokensInvalid = outputTokens === null;

  async function handleSave() {
    if (outputTokens === null) return;
    setSaving(true);
    setError(null);
    try {
      if (keyringOk && tokenInput.trim()) {
        await bridge.setHfToken(tokenInput.trim());
      }
      await onSave({
        default_output_tokens: outputTokens,
        currency,
        show_chunk_warnings: chunkWarnings,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof BridgeError ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleClearToken() {
    await bridge.deleteHfToken();
    setHasToken(false);
    setTokenInput("");
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        onCloseAutoFocus={(e) => {
          e.preventDefault();
          openerRef.current?.focus();
        }}
      >
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Defaults, currency, and API tokens.</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label htmlFor="settings-currency">Default currency</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger id="settings-currency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="settings-output-tokens">
              Default output tokens estimate
            </Label>
            <Input
              id="settings-output-tokens"
              value={outputTokensRaw}
              onChange={(e) => setOutputTokensRaw(e.target.value)}
              aria-invalid={outputTokensInvalid || undefined}
              inputMode="numeric"
            />
            {outputTokensInvalid && (
              <p className="type-small text-destructive">Enter a whole number.</p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="settings-hf-token">API tokens &amp; secrets</Label>
            <p className="type-small text-muted-foreground">
              {keyringOk
                ? "Stored in your OS keychain, never written to disk in plaintext. Used only for HuggingFace tokenizer downloads."
                : "No system keychain found — secure token storage is unavailable here."}
            </p>
            <div className="flex gap-2">
              <Input
                id="settings-hf-token"
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder={
                  hasToken ? "Token saved — leave blank to keep" : "hf_xxx (optional)"
                }
                disabled={!keyringOk}
              />
              <Button
                type="button"
                variant="secondary"
                disabled={!hasToken}
                onClick={handleClearToken}
              >
                Clear
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="type-label">Show chunk warnings</p>
              <p className="type-small text-muted-foreground">
                Alert when files exceed the context window
              </p>
            </div>
            <Switch checked={chunkWarnings} onCheckedChange={setChunkWarnings} />
          </div>

          {error && <p className="type-small text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={outputTokensInvalid || saving}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
