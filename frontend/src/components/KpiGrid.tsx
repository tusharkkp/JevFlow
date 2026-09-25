"use client";

import React from "react";
import { TelemetrySummary } from "@/lib/types";
import { TrendingDown, Zap, Clock, ShieldAlert, Cpu } from "lucide-react";

interface KpiGridProps {
  summary: TelemetrySummary | null;
}

export function KpiGrid({ summary }: KpiGridProps) {
  const totalReqs = summary?.total_requests || 0;
  const costSaved = summary?.total_cost_saved_usd || 0;
  const costReduction = summary?.cost_reduction_percent || 0;
  const p50 = summary?.p50_latency_ms || 0;
  const p95 = summary?.p95_latency_ms || 0;
  const p99 = summary?.p99_latency_ms || 0;
  const cacheHitRate = summary?.cache_hit_rate_percent || 0;

  const routeDist = summary?.route_distribution || {};

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px", marginBottom: "24px" }}>
      
      {/* 1. Requests Evaluated */}
      <div className="glass-panel" style={{ padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: "600" }}>
            Total Requests
          </span>
          <div style={{ padding: "6px", borderRadius: "8px", background: "rgba(56, 189, 248, 0.1)" }}>
            <Cpu size={16} color="#38bdf8" />
          </div>
        </div>
        <div style={{ fontSize: "2rem", fontWeight: "800", fontFamily: "var(--font-mono)" }}>
          {totalReqs.toLocaleString()}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "6px" }}>
          Evaluated via System One Pipeline
        </div>
      </div>

      {/* 2. Cumulative Cost Savings */}
      <div className="glass-panel" style={{ padding: "20px", position: "relative", overflow: "hidden" }}>
        <div style={{
          position: "absolute",
          top: "-20px",
          right: "-20px",
          width: "100px",
          height: "100px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(16, 185, 129, 0.15) 0%, transparent 70%)",
          pointerEvents: "none"
        }} />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: "600" }}>
            Net Cost Saved
          </span>
          <div style={{ padding: "6px", borderRadius: "8px", background: "rgba(16, 185, 129, 0.1)" }}>
            <TrendingDown size={16} color="#10b981" />
          </div>
        </div>
        <div className="gradient-cost" style={{ fontSize: "2rem", fontWeight: "800", fontFamily: "var(--font-mono)" }}>
          ${costSaved.toFixed(4)}
        </div>
        <div style={{ fontSize: "0.8rem", color: "#34d399", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
          <span><strong>{costReduction}%</strong> reduction vs 100% Frontier</span>
        </div>
      </div>

      {/* 3. P50 Latency */}
      <div className="glass-panel" style={{ padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: "600" }}>
            Median Latency (P50)
          </span>
          <div style={{ padding: "6px", borderRadius: "8px", background: "rgba(245, 158, 11, 0.1)" }}>
            <Zap size={16} color="#f59e0b" />
          </div>
        </div>
        <div style={{ fontSize: "2rem", fontWeight: "800", fontFamily: "var(--font-mono)" }}>
          {p50.toFixed(1)} <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: "500" }}>ms</span>
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "6px" }}>
          Cache hit rate: <strong style={{ color: "#38bdf8" }}>{cacheHitRate}%</strong>
        </div>
      </div>

      {/* 4. Tail Latency (P95 / P99) */}
      <div className="glass-panel" style={{ padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: "600" }}>
            Tail Latency (P95 / P99)
          </span>
          <div style={{ padding: "6px", borderRadius: "8px", background: "rgba(168, 85, 247, 0.1)" }}>
            <Clock size={16} color="#a855f7" />
          </div>
        </div>
        <div style={{ fontSize: "1.75rem", fontWeight: "800", fontFamily: "var(--font-mono)", display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span>{p95.toFixed(0)}</span>
          <span style={{ fontSize: "0.9rem", color: "var(--text-faint)" }}>/</span>
          <span style={{ color: "#c084fc" }}>{p99.toFixed(0)}</span>
          <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: "500" }}>ms</span>
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "6px" }}>
          Outlier tolerance SLA threshold
        </div>
      </div>

      {/* 5. Route Allocation Breakdown Banner */}
      <div className="glass-panel" style={{ gridColumn: "1 / -1", padding: "18px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: "600" }}>
            Traffic Route Allocation
          </span>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {Object.entries(routeDist).map(([r, data]) => (
              <span key={r} className={`badge badge-${r}`}>
                {r.replace("_", " ")}: {data.percentage}% ({data.count})
              </span>
            ))}
          </div>
        </div>

        {/* Visual Multi-segment bar */}
        <div style={{
          display: "flex",
          height: "10px",
          borderRadius: "5px",
          overflow: "hidden",
          background: "rgba(0,0,0,0.5)",
          border: "1px solid var(--border-subtle)"
        }}>
          {Object.entries(routeDist).map(([r, data]) => {
            let bg = "#3b82f6";
            if (r === "deterministic") bg = "#10b981";
            if (r === "cache") bg = "#06b6d4";
            if (r === "small_model") bg = "#f59e0b";
            if (r === "frontier_model") bg = "#a855f7";
            if (r === "human_review") bg = "#f43f5e";
            if (r === "fallback") bg = "#ef4444";

            return (
              <div
                key={r}
                title={`${r}: ${data.percentage}%`}
                style={{
                  width: `${data.percentage}%`,
                  backgroundColor: bg,
                  transition: "width 0.4s ease"
                }}
              />
            );
          })}
        </div>
      </div>

    </div>
  );
}
