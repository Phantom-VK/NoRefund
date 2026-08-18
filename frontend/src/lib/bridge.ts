import type {
  AnalysisResult,
  ExchangeRates,
  FitResult,
  HardwareTarget,
  ModelArchitecture,
  ModelComparison,
  ModelInfo,
  PortfolioProjection,
  ResourceReport,
  Settings,
} from "./types";

type Envelope<T> = { ok: true; data: T } | { ok: false; error: string };

declare global {
  interface Window {
    pywebview?: { api: Record<string, (...args: unknown[]) => Promise<unknown>> };
  }
}

export class BridgeError extends Error {}

/** The one place the bridge's return type is unchecked — narrowed
 *  immediately below via the `ok`/`error` envelope check. */
async function call<T>(method: string, ...args: unknown[]): Promise<T> {
  const api = window.pywebview?.api;
  if (!api) throw new BridgeError("Python bridge is not ready");
  const fn = api[method];
  if (!fn) throw new BridgeError(`Unknown bridge method: ${method}`);
  const raw = (await fn(...args)) as Envelope<T>;
  if (!raw || typeof raw !== "object" || !("ok" in raw)) {
    throw new BridgeError(`Malformed response from ${method}`);
  }
  if (!raw.ok) throw new BridgeError(raw.error);
  return raw.data;
}

/** Resolves once pywebview has injected the api object. */
export function bridgeReady(): Promise<void> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + 10_000;
    const poll = () => {
      if (window.pywebview?.api) {
        resolve();
        return;
      }
      if (Date.now() > deadline) {
        reject(new BridgeError("Python bridge did not become ready in time"));
        return;
      }
      setTimeout(poll, 25);
    };
    poll();
  });
}

export interface QuantizationOption {
  value: string;
  label: string;
}

export interface ProjectCostsResult {
  projections: PortfolioProjection[];
  cheapest: PortfolioProjection | null;
}

export const bridge = {
  // -- app metadata -------------------------------------------------------
  getAppVersion: () => call<string>("get_app_version"),

  // -- registry / static data --------------------------------------------
  getModels: () => call<ModelInfo[]>("get_models"),
  getArchitectures: () => call<ModelArchitecture[]>("get_architectures"),
  getHardware: () => call<HardwareTarget[]>("get_hardware"),
  getQuantizationLevels: () => call<QuantizationOption[]>("get_quantization_levels"),
  getKvCacheDtypes: () => call<QuantizationOption[]>("get_kv_cache_dtypes"),

  // -- settings & secrets --------------------------------------------------
  getSettings: () => call<Settings>("get_settings"),
  saveSettings: (settings: Settings) => call<Settings>("save_settings", settings),
  keyringAvailable: () => call<boolean>("keyring_available"),
  hasHfToken: () => call<boolean>("has_hf_token"),
  setHfToken: (token: string) => call<void>("set_hf_token", token),
  deleteHfToken: () => call<void>("delete_hf_token"),

  // -- currency ---------------------------------------------------------------
  getExchangeRates: () => call<ExchangeRates>("get_exchange_rates"),
  refreshExchangeRates: () => call<ExchangeRates>("refresh_exchange_rates"),

  // -- native dialogs -------------------------------------------------------
  pickFiles: () => call<string[]>("pick_files"),
  pickFolder: () => call<string | null>("pick_folder"),
  saveFile: (suggestedName: string, extension: string, label: string) =>
    call<string | null>("save_file", suggestedName, extension, label),

  // -- jobs ------------------------------------------------------------------
  startAnalysis: (paths: string[], modelId: string) =>
    call<string>("start_analysis", paths, modelId),
  startCompare: (
    text: string,
    paths: string[],
    modelIds: string[],
    outputTokens: number,
  ) => call<string>("start_compare", text, paths, modelIds, outputTokens),
  startResourceScan: () => call<string>("start_resource_scan"),
  startDownload: (resourceKey: string) => call<string>("start_download", resourceKey),
  cancelJob: (jobId: string) => call<boolean>("cancel_job", jobId),

  // -- synchronous compute ----------------------------------------------
  evaluateFit: (
    architectureId: string,
    hardwareId: string,
    quantization: string,
    contextLength: number,
    kvCacheDtype: string,
    concurrency = 1,
  ) =>
    call<FitResult>(
      "evaluate_fit",
      architectureId,
      hardwareId,
      quantization,
      contextLength,
      kvCacheDtype,
      concurrency,
    ),
  projectCosts: (
    corpusTokens: Record<string, number>,
    outputTokens: number,
    runsPerPeriod: number,
    frequency: string,
    modelIds: string[],
  ) =>
    call<ProjectCostsResult>(
      "project_costs",
      corpusTokens,
      outputTokens,
      runsPerPeriod,
      frequency,
      modelIds,
    ),
  whatIf: (report: ModelComparison, outputTokens: number) =>
    call<ModelComparison>("what_if", report, outputTokens),

  // -- export ----------------------------------------------------------------
  exportAnalysis: (results: AnalysisResult[], fmt: string) =>
    call<string | null>("export_analysis", results, fmt),
  exportComparison: (
    report: { source_label: string; results: ModelComparison[] },
    projections: PortfolioProjection[] | null,
    frequencyLabel: string | null,
    fmt: string,
  ) =>
    call<string | null>(
      "export_comparison",
      report,
      projections,
      frequencyLabel,
      fmt,
    ),
  exportFit: (fit: FitResult, names: Record<string, string | null>, fmt: string) =>
    call<string | null>("export_fit", fit, names, fmt),
  openPath: (path: string) => call<boolean>("open_path", path),
  openUrl: (url: string) => call<boolean>("open_url", url),
} as const;

export type { ResourceReport };
