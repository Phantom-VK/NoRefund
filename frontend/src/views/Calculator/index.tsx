import { Calculator as CalculatorIcon } from "lucide-react";
import { EmptyState } from "@/components/app/EmptyState";

export default function Calculator() {
  return (
    <EmptyState
      icon={CalculatorIcon}
      title="Token Calculator"
      description="This view is coming in a later phase."
    />
  );
}
