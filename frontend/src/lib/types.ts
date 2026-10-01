export type RouteType =
  | "deterministic"
  | "cache"
  | "small_model"
  | "frontier_model"
  | "human_review"
  | "fallback";

export interface TelemetryTrace {
  request_id: string;
  timestamp: string;
  intent: string;
  complexity_score: number;
  jev_confidence: number;
  selected_route: RouteType;
  policy_reason: string;
  actual_model: string;
  cache_hit: boolean;
  fallback_triggered: boolean;
  fallback_reason?: string | null;
  retries_attempted: number;
  circuit_breaker_tripped: boolean;
  error_category?: string | null;
  jev_latency_ms: number;
  model_latency_ms: number;
  gateway_overhead_ms: number;
  total_latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  baseline_cost_usd: number;
  cost_saved_usd: number;
  waterfall?: {
    jev_decision_ms: number;
    model_execution_ms: number;
    gateway_overhead_ms: number;
    total_end_to_end_ms: number;
  };
  economics?: {
    input_tokens: number;
    output_tokens: number;
    estimated_cost_usd: number;
    baseline_cost_usd: number;
    cost_saved_usd: number;
  };
}

export interface GatewayResponse {
  request_id: string;
  content: string;
  route: RouteType;
  model: string;
  telemetry: TelemetryTrace;
}

export interface TelemetrySummary {
  total_requests: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  average_latency_ms: number;
  total_cost_usd: number;
  total_cost_saved_usd: number;
  cost_reduction_percent: number;
  cache_hit_rate_percent: number;
  fallback_rate_percent: number;
  circuit_breaker_trip_count: number;
  route_distribution: Record<string, { count?: number; percentage: number } | number>;
}

export interface BenchmarkStrategyResult {
  strategy: string;
  requests_count: number;
  accuracy_route_match_percent: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  average_latency_ms: number;
  total_cost_usd: number;
  baseline_cost_usd: number;
  total_cost_saved_usd: number;
  cost_reduction_percent: number;
  cache_hit_rate: number;
  fallback_rate: number;
}

export interface BenchmarkReport {
  baseline?: BenchmarkStrategyResult;
  rules?: BenchmarkStrategyResult;
  jevflow?: BenchmarkStrategyResult;
}

export interface GatewayHealth {
  status: string;
  app: string;
  version: string;
  active_decision_engine: string;
}

export interface CacheStats {
  backend: string;
  size: number;
  max_size: number;
  status: string;
  active_entries?: number;
  max_entries?: number;
}

export interface RateLimitStats {
  rate_limit_per_second: number;
  capacity: number;
  tracked_clients_count: number;
  refill_rate_per_sec?: number;
  burst_capacity?: number;
  active_buckets?: number;
}

export interface ExperimentListItem {
  experiment_id: string;
  name: string;
  strategy: string;
  created_at: string;
  total_requests: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  average_latency_ms: number;
  total_cost_usd: number;
  cost_saved_usd: number;
  average_cost_per_request: number;
  success_rate: number;
  fallback_rate: number;
  cache_hit_rate: number;
}
