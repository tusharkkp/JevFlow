import {
  GatewayHealth,
  GatewayResponse,
  TelemetrySummary,
  TelemetryTrace,
  BenchmarkReport,
  CacheStats,
  RateLimitStats,
  ExperimentListItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8000";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const err = await res.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      // ignore
    }
    throw new Error(`API Error (${res.status}): ${errorDetail}`);
  }

  return res.json();
}

export const api = {
  async getHealth(): Promise<GatewayHealth> {
    return fetchJson<GatewayHealth>(`${API_BASE}/health`);
  },

  async getCacheStats(): Promise<CacheStats> {
    return fetchJson<CacheStats>(`${API_BASE}/v1/cache/stats`);
  },

  async clearCache(): Promise<{ status: string }> {
    return fetchJson<{ status: string }>(`${API_BASE}/v1/cache/clear`, {
      method: "POST",
    });
  },

  async getRateLimitStats(): Promise<RateLimitStats> {
    return fetchJson<RateLimitStats>(`${API_BASE}/v1/rate-limit/stats`);
  },

  async getTelemetrySummary(): Promise<TelemetrySummary> {
    return fetchJson<TelemetrySummary>(`${API_BASE}/v1/telemetry/summary`);
  },

  async listTraces(limit = 30, offset = 0, route?: string): Promise<TelemetryTrace[]> {
    const url = new URL(`${API_BASE}/v1/telemetry/requests`);
    url.searchParams.set("limit", String(limit));
    url.searchParams.set("offset", String(offset));
    if (route && route !== "all") {
      url.searchParams.set("route", route);
    }
    return fetchJson<TelemetryTrace[]>(url.toString());
  },

  async getTrace(requestId: string): Promise<TelemetryTrace> {
    return fetchJson<TelemetryTrace>(`${API_BASE}/v1/telemetry/requests/${requestId}`);
  },

  async sendChat(
    prompt: string,
    latencyBudgetMs?: number,
    costBudget?: number
  ): Promise<GatewayResponse> {
    return fetchJson<GatewayResponse>(`${API_BASE}/v1/chat`, {
      method: "POST",
      body: JSON.stringify({
        prompt,
        latency_budget_ms: latencyBudgetMs || undefined,
        cost_budget: costBudget || undefined,
      }),
    });
  },

  async runBenchmark(strategy = "all"): Promise<BenchmarkReport> {
    return fetchJson<BenchmarkReport>(
      `${API_BASE}/v1/experiments/run?strategy=${strategy}`,
      { method: "POST" }
    );
  },

  async listExperiments(limit = 10, offset = 0): Promise<ExperimentListItem[]> {
    return fetchJson<ExperimentListItem[]>(`${API_BASE}/v1/experiments?limit=${limit}&offset=${offset}`);
  },
};
