import { useEffect, useState } from "react";
import { Card } from "@/components/app/Card";
import { EmptyState } from "@/components/app/EmptyState";
import { useApp } from "@/lib/appContext";
import { parseIntSafe } from "@/lib/format";
import { contextUsagePct, fitsInContext, inputCost, outputCost } from "@/lib/costing";
import type { ModelInfo } from "@/lib/types";
import { Calculator as CalculatorIcon } from "lucide-react";
import { ModelPicker } from "./ModelPicker";
import { TokenInputs } from "./TokenInputs";
import { ContextCard } from "./ContextCard";
import { CostCard } from "./CostCard";

export default function Calculator() {
  const { models, settings, exchangeRates } = useApp();
  const [modelId, setModelId] = useState(models[0]?.id ?? "");
  const [inputRaw, setInputRaw] = useState("0");
  const [outputRaw, setOutputRaw] = useState(String(settings.default_output_tokens));

  const model = models.find((m) => m.id === modelId);

  if (!model) {
    return (
      <EmptyState
        icon={CalculatorIcon}
        title="No models available"
        description="The model registry is empty."
      />
    );
  }

  function handleModelChange(m: ModelInfo) {
    setModelId(m.id);
    setOutputRaw(String(settings.default_output_tokens));
  }

  // Views stay mounted for the app's lifetime (see lib/views.ts), so this
  // component doesn't get to re-read settings.default_output_tokens simply
  // by remounting when the user changes it in the Settings modal -- without
  // this, the new default only took effect after switching models or
  // restarting the app.
  useEffect(() => {
    setOutputRaw(String(settings.default_output_tokens));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.default_output_tokens]);

  const inputTokens = parseIntSafe(inputRaw);
  const outputTokens = parseIntSafe(outputRaw);

  const pct = inputTokens === null ? null : contextUsagePct(inputTokens, model.context_window);
  const fits = inputTokens === null ? null : fitsInContext(inputTokens, model.context_window);
  const inCost = inputTokens === null ? null : inputCost(inputTokens, model);
  const outCost =
    outputTokens === null
      ? null
      : outputCost(outputTokens, model, inputTokens ?? undefined);
  const total = inCost === null || outCost === null ? null : inCost + outCost;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <p className="type-body text-muted-foreground">
        Manually estimate token cost for any LLM before making an API call.
      </p>

      <Card>
        <div className="flex flex-col gap-4">
          <ModelPicker models={models} value={modelId} onChange={handleModelChange} />
          <TokenInputs
            inputRaw={inputRaw}
            outputRaw={outputRaw}
            inputValid={inputTokens !== null}
            outputValid={outputTokens !== null}
            onInputChange={setInputRaw}
            onOutputChange={setOutputRaw}
          />
        </div>
      </Card>

      <ContextCard
        pct={pct}
        inputTokens={inputTokens}
        contextWindow={model.context_window}
        fits={fits}
        showWarnings={settings.show_chunk_warnings}
      />

      <CostCard
        inputCost={inCost}
        outputCost={outCost}
        totalCost={total}
        model={model}
        currency={settings.currency}
        rates={exchangeRates}
      />
    </div>
  );
}
