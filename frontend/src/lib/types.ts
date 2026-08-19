// One interface per core dataclass, field-for-field. Field names are
// snake_case, matching the wire format exactly — see
// src/norefund/desktop/dto.py's docstring. A pytest contract test
// (tests/test_desktop_api.py) asserts these stay in sync with the Python
// dataclasses; if you change a field here, change it there too.

export interface ModelInfo {
  id: string;
  display_name: string;
  provider: string;
  tokenizer_backend: string;
  tokenizer_name: string;
  context_window: number;
  input_price_per_million: number;
  output_price_per_million: number;
  currency: string;
  docs_url: string | null;
  tokenizer_is_approximate: boolean;
}

export interface AnalysisResult {
  file_path: string;
  model_id: string;
  char_count: number;
  word_count: number;
  token_count: number;
  context_window: number;
  context_usage_pct: number | null;
  fits_in_context: boolean;
  min_chunks_needed: number;
  estimated_input_cost: number;
  error: string | null;
}

export interface ModelComparison {
  model: ModelInfo;
  token_count: number;
  context_usage_pct: number | null;
  fits_in_context: boolean;
  min_chunks_needed: number;
  output_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
  tokenizer_is_approximate: boolean;
  error: string | null;
}

export interface CompareReport {
  source_label: string;
  results: ModelComparison[];
}

export interface PortfolioProjection {
  model: ModelInfo;
  corpus_tokens: number;
  fits_in_context: boolean;
  cost_per_run: number;
  monthly_cost: number;
  annual_cost: number;
}

export interface MemoryEstimate {
  weights_bytes: number;
  kv_cache_bytes_per_sequence: number;
  kv_cache_bytes: number;
  activation_bytes: number;
  framework_overhead_bytes: number;
  total_bytes: number;
}

export interface FitResult {
  architecture_id: string;
  hardware_id: string;
  quantization: string;
  kv_cache_dtype: string;
  context_length: number;
  concurrency: number;
  usable_memory_bytes: number;
  estimate: MemoryEstimate | null;
  fits: boolean;
  headroom_bytes: number | null;
  utilization_pct: number | null;
  max_concurrent_requests: number | null;
  warnings: string[];
  error: string | null;
}

export interface ModelArchitecture {
  id: string;
  display_name: string;
  family: string;
  vendor: string;
  total_params: number;
  active_params: number;
  n_layers: number;
  n_attention_heads: number;
  n_kv_heads: number;
  head_dim: number;
  hidden_size: number;
  max_context_length: number;
  attention_type: string;
  kv_lora_rank: number;
  qk_rope_head_dim: number;
  docs_url: string | null;
}

export interface HardwareTarget {
  id: string;
  display_name: string;
  category: string;
  vendor: string;
  accelerator: string;
  device_count: number;
  memory_gib_per_device: number;
  memory_kind: string;
  usable_memory_fraction: number;
  notes: string | null;
}

export interface TokenizerResource {
  key: string;
  backend: "tiktoken" | "hf";
  name: string;
  model_ids: string[];
  is_cached: boolean;
  cache_path: string | null;
  size_bytes: number | null;
  source_url: string | null;
  notes: string | null;
}

export interface ManagedDir {
  label: string;
  path: string;
  exists: boolean;
  size_bytes: number;
  file_count: number;
}

export interface ResourceReport {
  tokenizers: TokenizerResource[];
  dirs: ManagedDir[];
  total_tokenizer_bytes: number;
}

export interface Settings {
  default_output_tokens: number;
  theme: "system" | "light" | "dark";
  currency: string;
  show_chunk_warnings: boolean;
  onboarding_dismissed: boolean;
}

export interface ExchangeRates {
  base: string;
  rates: Record<string, number>;
  fetched_at: string | null;
}

export interface LogEntry {
  level: string;
  message: string;
  ctx: Record<string, unknown>;
}

export type JobKind = "progress" | "done" | "error" | "cancelled";
export interface JobEventDetail<T = unknown> {
  job_id: string;
  kind: JobKind;
  payload: T;
}
