"use client";

import React from "react";
import { GatewayHealth, CacheStats, RateLimitStats } from "@/lib/types";
import { Activity, ShieldCheck, Database, RefreshCw, Zap } from "lucide-react";

interface HeaderProps {
  health: GatewayHealth | null;
  cache: CacheStats | null;
  rateLimit: RateLimitStats | null;
  refreshing: boolean;
  onRefresh: () => void;
}

export function Header({
  health,
  cache,
  rateLimit,
  refreshing,
  onRefresh,
}: HeaderProps) {
  const isHealthy = health?.status === "ok";

  return (
    <header className="glass-panel" style={{ padding: "16px 24px", marginBottom: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        
        {/* Brand & Subtitle */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "42px",
            height: "42px",
            borderRadius: "12px",
            background: "linear-gradient(135deg, #0284c7 0%, #a855f7 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 20px rgba(56, 189, 248, 0.3)"
          }}>
            <Zap size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 className="gradient-title" style={{ fontSize: "1.35rem", fontWeight: "800", letterSpacing: "-0.5px" }}>
                JEVFLOW
              </h1>
              <span className="badge badge-cache" style={{ fontSize: "0.68rem" }}>
                v{health?.version || "0.8.0"}
              </span>
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "2px" }}>
              Adaptive AI Gateway powered by System One Probabilistic Decisions &amp; Deterministic Policy
            </p>
          </div>
        </div>

        {/* Live System Health Indicators */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          
          {/* Gateway Status */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(0,0,0,0.3)",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
          }}>
            <span className={`pulse-dot ${isHealthy ? "pulse-green" : "pulse-red"}`} />
            <span style={{ color: "var(--text-muted)" }}>Gateway:</span>
            <strong style={{ color: isHealthy ? "#34d399" : "#f87171" }}>
              {isHealthy ? "ONLINE" : "OFFLINE"}
            </strong>
          </div>

          {/* Decision Engine */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(0,0,0,0.3)",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
          }}>
            <Activity size={14} color="#38bdf8" />
            <span style={{ color: "var(--text-muted)" }}>Engine:</span>
            <span style={{ color: "#38bdf8", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
              {health?.active_decision_engine || "TypeSafe Jev"}
            </span>
          </div>

          {/* Cache Status */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(0,0,0,0.3)",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
          }}>
            <Database size={14} color="#a855f7" />
            <span style={{ color: "var(--text-muted)" }}>Cache:</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#c084fc" }}>
              {cache ? `${cache.size} / ${cache.max_size} entries` : "Active"}
            </span>
          </div>

          {/* Rate Limiter */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(0,0,0,0.3)",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
          }}>
            <ShieldCheck size={14} color="#10b981" />
            <span style={{ color: "var(--text-muted)" }}>Rate Limiter:</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#34d399" }}>
              {rateLimit ? `${rateLimit.rate_limit_per_second} req/s` : "10 req/s"}
            </span>
          </div>

          {/* Manual Refresh */}
          <button
            id="btn-refresh-telemetry"
            className="btn-secondary"
            onClick={onRefresh}
            disabled={refreshing}
            title="Refresh Gateway Metrics"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} style={{
              animation: refreshing ? "spin 1s linear infinite" : "none"
            }} />
            <span>Sync</span>
          </button>

        </div>

      </div>
    </header>
  );
}
