import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/app/Card";
import { Spinner } from "@/components/app/Spinner";
import { StatPill } from "@/components/app/StatPill";
import { useApp } from "@/lib/appContext";
import { bridge, BridgeError } from "@/lib/bridge";
import { fmtNum, parseIntSafe } from "@/lib/format";
import type { FitResult, HardwareTarget, ModelArchitecture } from "@/lib/types";
import type { QuantizationOption } from "@/lib/bridge";
import { VerdictHeader } from "./VerdictHeader";
import { UtilizationCard } from "./UtilizationCard";
import { BreakdownCard } from "./BreakdownCard";
import { ConfigCard } from "./ConfigCard";
import { Warnings } from "./Warnings";

const DEFAULT_CONTEXT = "8192";
const DEFAULT_QUANTIZATION = "q4_k_m";
const DEFAULT_KV_CACHE_DTYPE = "fp16";

function localError(
  architectureId: string,
  hardwareId: string,
  quantization: string,
  kvCacheDtype: string,
  message: string,
): FitResult {
  return {
    architecture_id: architectureId,
    hardware_id: hardwareId,
    quantization,
    kv_cache_dtype: kvCacheDtype,
    context_length: 0,
    concurrency: 0,
    usable_memory_bytes: 0,
    estimate: null,
    fits: false,
    headroom_bytes: null,
    utilization_pct: null,
    max_concurrent_requests: null,
    warnings: [],
    error: message,
  };
}

export default function FitCheck() {
  const { lastAnalysisTokens } = useApp();

  const [architectures, setArchitectures] = useState<ModelArchitecture[] | null>(null);
  const [hardware, setHardware] = useState<HardwareTarget[] | null>(null);
  const [quantLevels, setQuantLevels] = useState<QuantizationOption[] | null>(null);
  const [kvDtypes, setKvDtypes] = useState<QuantizationOption[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [architectureId, setArchitectureId] = useState("");
  const [hardwareId, setHardwareId] = useState("");
  const [quantization, setQuantization] = useState(DEFAULT_QUANTIZATION);
  const [kvCacheDtype, setKvCacheDtype] = useState(DEFAULT_KV_CACHE_DTYPE);
  const [context, setContext] = useState(DEFAULT_CONTEXT);
  const [contextEdited, setContextEdited] = useState(false);
  const lastAutofilled = useRef(DEFAULT_CONTEXT);

  const [fit, setFit] = useState<FitResult | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      bridge.getArchitectures(),
      bridge.getHardware(),
      bridge.getQuantizationLevels(),
      bridge.getKvCacheDtypes(),
    ])
      .then(([archs, hw, quants, kvs]) => {
        if (cancelled) return;
        setArchitectures(archs);
        setHardware(hw);
        setQuantLevels(quants);
        setKvDtypes(kvs);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(bridgeErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (architectures && architectures.length > 0 && architectureId === "") {
      setArchitectureId(architectures[0].id);
    }
  }, [architectures, architectureId]);

  useEffect(() => {
    if (hardware && hardware.length > 0 && hardwareId === "") {
      setHardwareId(hardware[0].id);
    }
  }, [hardware, hardwareId]);

  // Gate auto-fill on the value actually changing, not on any keystroke --
  // Tab, arrow keys, or a Ctrl+C copy fire a real DOM event in Tk but never
  // an onChange here, so this is mostly free; the explicit comparison keeps
  // the intent obvious if the input is ever swapped for something looser.
  function handleContextChange(next: string) {
    setContext(next);
    if (next !== lastAutofilled.current) setContextEdited(true);
  }

  // Views stay mounted for the app's lifetime, so this doesn't get to
  // prefill by remounting when the user finishes a Parser analysis --
  // this effect is what makes "navigate here after analyzing" and "analyze
  // while already here" both work, as long as the field hasn't been touched.
  useEffect(() => {
    if (contextEdited || !lastAnalysisTokens) return;
    const value = String(lastAnalysisTokens);
    setContext(value);
    lastAutofilled.current = value;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastAnalysisTokens]);

  const contextTokens = parseIntSafe(context);
  const ready = architectureId !== "" && hardwareId !== "";

  // The `cancelled` flag stops an out-of-order response from a slower
  // earlier call overwriting a newer result -- with five rapidly-changing
  // inputs this is a real race, not a theoretical one.
  useEffect(() => {
    if (!ready) return;
    // A prior "Exported to ..." status refers to whatever configuration was
    // current at export time -- once the config changes and a new fit is
    // being computed, that status is stale and would otherwise sit there
    // (even through a later cancelled export) implying the *current*
    // config was just exported.
    setStatus(null);
    if (contextTokens === null) {
      setFit(
        localError(
          architectureId,
          hardwareId,
          quantization,
          kvCacheDtype,
          "Context length must be a positive whole number.",
        ),
      );
      return;
    }
    let cancelled = false;
    bridge
      .evaluateFit(architectureId, hardwareId, quantization, contextTokens, kvCacheDtype)
      .then((r) => {
        if (!cancelled) setFit(r);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setFit(
            localError(architectureId, hardwareId, quantization, kvCacheDtype, bridgeErrorMessage(err)),
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [ready, architectureId, hardwareId, quantization, kvCacheDtype, contextTokens]);

  async function handleExport(fmt: "pdf" | "html") {
    if (!fit) return;
    try {
      const names = {
        architecture: architectures?.find((a) => a.id === architectureId)?.display_name ?? null,
        hardware: hardware?.find((h) => h.id === hardwareId)?.display_name ?? null,
        quantization: quantLevels?.find((q) => q.value === quantization)?.label ?? null,
        kv_cache: kvDtypes?.find((d) => d.value === kvCacheDtype)?.label ?? null,
      };
      const path = await bridge.exportFit(fit, names, fmt);
      if (path) setStatus(`Exported to ${path}`);
    } catch (err) {
      setStatus(`Export failed: ${bridgeErrorMessage(err)}`);
    }
  }

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center">
        <p className="type-body text-destructive">{loadError}</p>
      </div>
    );
  }

  if (!architectures || !hardware || !quantLevels || !kvDtypes) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size={32} />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <VerdictHeader
        fit={fit}
        onExportPdf={() => void handleExport("pdf")}
        onExportHtml={() => void handleExport("html")}
      />

      <UtilizationCard pct={fit?.error ? null : (fit?.utilization_pct ?? null)} />

      <BreakdownCard
        estimate={fit?.error ? null : (fit?.estimate ?? null)}
        headroomBytes={fit?.error ? null : (fit?.headroom_bytes ?? null)}
      />

      <Card className="p-4">
        <StatPill
          label="Max concurrent requests"
          value={
            !fit?.error && fit?.max_concurrent_requests != null
              ? fmtNum(fit.max_concurrent_requests)
              : "—"
          }
          mono
        />
      </Card>

      <ConfigCard
        architectures={architectures}
        hardware={hardware}
        quantLevels={quantLevels}
        kvDtypes={kvDtypes}
        architectureId={architectureId}
        onArchitectureChange={setArchitectureId}
        hardwareId={hardwareId}
        onHardwareChange={setHardwareId}
        quantization={quantization}
        onQuantizationChange={setQuantization}
        kvCacheDtype={kvCacheDtype}
        onKvCacheDtypeChange={setKvCacheDtype}
        context={context}
        onContextChange={handleContextChange}
        contextValid={contextTokens !== null}
      />

      <Warnings warnings={fit?.error ? [] : (fit?.warnings ?? [])} />

      {status && <p className="type-small text-muted-foreground">{status}</p>}
    </div>
  );
}

function bridgeErrorMessage(err: unknown): string {
  return err instanceof BridgeError ? err.message : String(err);
}
