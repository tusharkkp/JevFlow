"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  GatewayHealth,
  CacheStats,
  RateLimitStats,
  TelemetrySummary,
  TelemetryTrace,
  BenchmarkReport,
} from "@/lib/types";
import { api } from "@/lib/api";
import { Header } from "@/components/Header";
import { KpiGrid } from "@/components/KpiGrid";
import { Playground } from "@/components/Playground";
import { TraceTable } from "@/components/TraceTable";
import { BenchmarkView } from "@/components/BenchmarkView";
import { Layers, Sparkles, Clock, BarChart3 } from "lucide-react";

export default function DashboardPage() {
  const [health, setHealth] = useState<GatewayHealth | null>(null);
  const [cache, setCache] = useState<CacheStats | null>(null);
  const [rateLimit, setRateLimit] = useState<RateLimitStats | null>(null);
  const [summary, setSummary] = useState<TelemetrySummary | null>(null);
  const [traces, setTraces] = useState<TelemetryTrace[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<string>("all");
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "playground" | "traces" | "benchmarks">("overview");

  // Pre-load benchmark data if available
  const [initialBenchmark, setInitialBenchmark] = useState<BenchmarkReport | null>(null);

  const fetchAllData = useCallback(async () => {
    setRefreshing(true);
    try {
      const [h, c, r, s, t] = await Promise.allSettled([
        api.getHealth(),
        api.getCacheStats(),
        api.getRateLimitStats(),
        api.getTelemetrySummary(),
        api.listTraces(30, 0, selectedRoute),
      ]);

      if (h.status === "fulfilled") setHealth(h.value);
      if (c.status === "fulfilled") setCache(c.value);
      if (r.status === "fulfilled") setRateLimit(r.value);
      if (s.status === "fulfilled") setSummary(s.value);
      if (t.status === "fulfilled") setTraces(t.value);
    } finally {
      setRefreshing(false);
    }
  }, [selectedRoute]);

  // Initial load
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Auto-refresh polling every 10 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      fetchAllData();
    }, 10000);
    return () => clearInterval(timer);
  }, [fetchAllData]);

  return (
    <main style={{ maxWidth: "1400px", margin: "0 auto", padding: "24px 20px" }}>
      
      {/* Header & Health Bar */}
      <Header
        health={health}
        cache={cache}
        rateLimit={rateLimit}
        refreshing={refreshing}
        onRefresh={fetchAllData}
      />

      {/* KPI Overview Metrics Cards */}
      <KpiGrid summary={summary} />

      {/* Navigation Tab Bar */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
        <button
          className={`btn-secondary ${activeTab === "overview" ? "badge-cache" : ""}`}
          style={{ borderColor: activeTab === "overview" ? "var(--border-focus)" : "var(--border-subtle)" }}
          onClick={() => setActiveTab("overview")}
        >
          <Layers size={15} />
          <span>Full Dashboard</span>
        </button>

        <button
          className={`btn-secondary ${activeTab === "playground" ? "badge-cache" : ""}`}
          style={{ borderColor: activeTab === "playground" ? "var(--border-focus)" : "var(--border-subtle)" }}
          onClick={() => setActiveTab("playground")}
        >
          <Sparkles size={15} />
          <span>Routing Playground</span>
        </button>

        <button
          className={`btn-secondary ${activeTab === "traces" ? "badge-cache" : ""}`}
          style={{ borderColor: activeTab === "traces" ? "var(--border-focus)" : "var(--border-subtle)" }}
          onClick={() => setActiveTab("traces")}
        >
          <Clock size={15} />
          <span>Trace Explorer</span>
        </button>

        <button
          className={`btn-secondary ${activeTab === "benchmarks" ? "badge-cache" : ""}`}
          style={{ borderColor: activeTab === "benchmarks" ? "var(--border-focus)" : "var(--border-subtle)" }}
          onClick={() => setActiveTab("benchmarks")}
        >
          <BarChart3 size={15} />
          <span>A/B Evaluation</span>
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === "overview" && (
        <>
          <Playground onExecuted={fetchAllData} />
          <TraceTable
            traces={traces}
            selectedRoute={selectedRoute}
            onFilterRoute={(r) => {
              setSelectedRoute(r);
            }}
            loading={refreshing}
          />
          <BenchmarkView
            initialReport={initialBenchmark}
            onBenchmarkCompleted={fetchAllData}
          />
        </>
      )}

      {activeTab === "playground" && (
        <Playground onExecuted={fetchAllData} />
      )}

      {activeTab === "traces" && (
        <TraceTable
          traces={traces}
          selectedRoute={selectedRoute}
          onFilterRoute={(r) => setSelectedRoute(r)}
          loading={refreshing}
        />
      )}

      {activeTab === "benchmarks" && (
        <BenchmarkView
          initialReport={initialBenchmark}
          onBenchmarkCompleted={fetchAllData}
        />
      )}

      {/* Footer */}
      <footer style={{ marginTop: "40px", textAlign: "center", color: "var(--text-faint)", fontSize: "0.78rem" }}>
        JevFlow Adaptive AI Gateway • Powered by System One Decisions &amp; Deterministic Policy • Built for Learning &amp; Production Reliability
      </footer>

    </main>
  );
}
