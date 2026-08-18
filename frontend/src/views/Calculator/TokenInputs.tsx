import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface TokenInputsProps {
  inputRaw: string;
  outputRaw: string;
  inputValid: boolean;
  outputValid: boolean;
  onInputChange: (v: string) => void;
  onOutputChange: (v: string) => void;
}

export function TokenInputs({
  inputRaw,
  outputRaw,
  inputValid,
  outputValid,
  onInputChange,
  onOutputChange,
}: TokenInputsProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="calc-input-tokens">Input tokens</Label>
        <Input
          id="calc-input-tokens"
          value={inputRaw}
          onChange={(e) => onInputChange(e.target.value)}
          inputMode="numeric"
          className="tabular font-mono type-title"
          aria-invalid={!inputValid || undefined}
        />
        {!inputValid && (
          <p className="type-small text-destructive">Enter a non-negative whole number.</p>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="calc-output-tokens">Est. output tokens</Label>
        <Input
          id="calc-output-tokens"
          value={outputRaw}
          onChange={(e) => onOutputChange(e.target.value)}
          inputMode="numeric"
          className="tabular font-mono type-title"
          aria-invalid={!outputValid || undefined}
        />
        {!outputValid && (
          <p className="type-small text-destructive">Enter a non-negative whole number.</p>
        )}
      </div>
    </div>
  );
}
