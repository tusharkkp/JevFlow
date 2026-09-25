"use client";

import React, { useState } from "react";
import { TelemetryTrace, RouteType } from "@/lib/types";
import { ListFilter, ChevronDown, ChevronRight, Clock, DollarSign, CheckCircle2, ShieldAlert } from "lucide-react";

interface TraceTableProps {
  traces: TelemetryTrace[];
  selectedRoute: string;
  onFilterRoute: (route: string) => void;
  loading: boolean;
}

const ROUTE_OPTIONS = [
  { value: "all", label: "All Routes" },
  { value: "deterministic", label: "Deterministic" },
  { value: "cache", label: "Cache" },
  { value: "small_model", label: "Small Model" },
  { value: "frontier_model", label: "Frontier Model" },
  { value: "human_review", label: "Human Review" },
  { value: "fallback", label: "Fallback" },
];

export function TraceTable({ traces, selectedRoute, onFilterRoute, loading }: TraceTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="glass-panel" style={{ padding: "24px", marginBottom: "24px" }}>
      
      {/* Title & Filter Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.15rem", fontWeight: "700", display: "flex", alignItems: "center", gap: "8px" }}>
            <Clock size={18} color="#10b981" />
            Live Trace Explorer &amp; Distributed Spans
          </h2>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "2px" }}>
            Real-time trace logs with granular sub-millisecond latency waterfalls and token economics.
          </p>
        </div>

        {/* Filter Pills */}
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {ROUTE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`btn-secondary ${selectedRoute === opt.value ? "badge-cache" : ""}`}
              style={{
                fontSize: "0.75rem",
                padding: "4px 10px",
                borderColor: selectedRoute === opt.value ? "var(--border-focus)" : "var(--border-subtle)",
              }}
              onClick={() => onFilterRoute(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
              <th style={{ padding: "10px 12px" }}>Request ID</th>
              <th style={{ padding: "10px 12px" }}>Timestamp</th>
              <th style={{ padding: "10px 12px" }}>Intent / Complexity</th>
              <th style={{ padding: "10px 12px" }}>Route &amp; Provider</th>
              <th style={{ padding: "10px 12px" }}>Latency Waterfall</th>
              <th style={{ padding: "10px 12px", textAlign: "right" }}>Cost Saved</th>
              <th style={{ padding: "10px 12px", textAlign: "center" }}>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {traces.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                  {loading ? "Loading trace events..." : "No requests found for this filter."}
                </td>
              </tr>
            ) : (
              traces.map((trace) => {
                const isExpanded = expandedId === trace.request_id;
                const timeStr = new Date(trace.timestamp).toLocaleTimeString();

                return (
                  <React.Fragment key={trace.request_id}>
                    <tr
                      onClick={() => toggleExpand(trace.request_id)}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        cursor: "pointer",
                        background: isExpanded ? "rgba(255,255,255,0.02)" : "transparent",
                        transition: "background 0.15s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "rgba(255, 255, 255, 0.04)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = isExpanded ? "rgba(255,255,255,0.02)" : "transparent";
                      }}
                    >
                      {/* Request ID */}
                      <td style={{ padding: "12px", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                        <span style={{ color: "var(--text-main)" }}>
                          {trace.request_id.slice(0, 16)}...
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td style={{ padding: "12px", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {timeStr}
                      </td>

                      {/* Intent & Complexity */}
                      <td style={{ padding: "12px" }}>
                        <div>
                          <span style={{ fontWeight: "600" }}>{trace.intent}</span>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>
                            Score: {trace.complexity_score.toFixed(2)} | Conf: {(trace.jev_confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>

                      {/* Route & Provider */}
                      <td style={{ padding: "12px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                          <span className={`badge badge-${trace.selected_route}`}>
                            {trace.selected_route.replace("_", " ")}
                          </span>
                          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                            {trace.actual_model}
                          </span>
                        </div>
                      </td>

                      {/* Latency Waterfall Bar Mini */}
                      <td style={{ padding: "12px", minWidth: "160px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <span style={{ fontSize: "0.78rem", fontWeight: "600" }}>
                            {trace.total_latency_ms.toFixed(1)} ms
                          </span>
                          <div style={{
                            display: "flex",
                            height: "6px",
                            borderRadius: "3px",
                            overflow: "hidden",
                            background: "rgba(0,0,0,0.5)",
                          }}>
                            {trace.jev_latency_ms > 0 && (
                              <div
                                style={{
                                  width: `${(trace.jev_latency_ms / trace.total_latency_ms) * 100}%`,
                                  background: "#3b82f6",
                                }}
                                title={`Jev: ${trace.jev_latency_ms}ms`}
                              />
                            )}
                            {trace.model_latency_ms > 0 && (
                              <div
                                style={{
                                  width: `${(trace.model_latency_ms / trace.total_latency_ms) * 100}%`,
                                  background: "#8b5cf6",
                                }}
                                title={`Model: ${trace.model_latency_ms}ms`}
                              />
                            )}
                            <div
                              style={{
                                width: `${(trace.gateway_overhead_ms / trace.total_latency_ms) * 100}%`,
                                background: "#10b981",
                              }}
                              title={`Overhead: ${trace.gateway_overhead_ms}ms`}
                            />
                          </div>
                        </div>
                      </td>

                      {/* Cost Saved */}
                      <td style={{ padding: "12px", textAlign: "right", fontFamily: "var(--font-mono)" }}>
                        {trace.cost_saved_usd > 0 ? (
                          <span style={{ color: "#34d399", fontWeight: "600" }}>
                            +${trace.cost_saved_usd.toFixed(6)}
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-faint)" }}>$0.00</span>
                        )}
                      </td>

                      {/* Toggle inspect */}
                      <td style={{ padding: "12px", textAlign: "center" }}>
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </td>
                    </tr>

                    {/* Expandable Waterfall & Diagnostics Panel */}
                    {isExpanded && (
                      <tr style={{ background: "rgba(10, 15, 28, 0.6)" }}>
                        <td colSpan={7} style={{ padding: "18px 24px", borderBottom: "1px solid var(--border-subtle)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
                            
                            {/* Latency Waterfall Details */}
                            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "var(--radius-sm)" }}>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                                Waterfall Latency Breakdown:
                              </span>
                              <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.8rem", fontFamily: "var(--font-mono)" }}>
                                <div style={{ display: "flex", justifyContent: "space-between" }}>
                                  <span style={{ color: "#38bdf8" }}>Jev Decision Hop:</span>
                                  <span>{trace.jev_latency_ms.toFixed(1)} ms</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between" }}>
                                  <span style={{ color: "#c084fc" }}>Model Provider Execution:</span>
                                  <span>{trace.model_latency_ms.toFixed(1)} ms</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between" }}>
                                  <span style={{ color: "#34d399" }}>Gateway Pipeline Overhead:</span>
                                  <span>{trace.gateway_overhead_ms.toFixed(1)} ms</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "4px", borderTop: "1px solid var(--border-subtle)", fontWeight: "700" }}>
                                  <span>Total End-to-End:</span>
                                  <span>{trace.total_latency_ms.toFixed(1)} ms</span>
                                </div>
                              </div>
                            </div>

                            {/* Economics Breakdown */}
                            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "var(--radius-sm)" }}>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                                Token Accounting &amp; Counter-Factual Economics:
                              </span>
                              <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.8rem", fontFamily: "var(--font-mono)" }}>
                                <div style={{ display: "flex", justifyContent: "space-between" }}>
                                  <span style={{ color: "var(--text-muted)" }}>Input / Output Tokens:</span>
                                  <span>{trace.input_tokens} / {trace.output_tokens}</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between" }}>
                                  <span style={{ color: "var(--text-muted)" }}>Actual Cost:</span>
                                  <span>${trace.estimated_cost_usd.toFixed(6)}</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between" }}>
                                  <span style={{ color: "var(--text-muted)" }}>Frontier Baseline Cost:</span>
                                  <span>${trace.baseline_cost_usd.toFixed(6)}</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "4px", borderTop: "1px solid var(--border-subtle)", color: "#34d399", fontWeight: "700" }}>
                                  <span>Net Money Saved:</span>
                                  <span>${trace.cost_saved_usd.toFixed(6)}</span>
                                </div>
                              </div>
                            </div>

                            {/* Policy & Diagnostics */}
                            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "var(--radius-sm)" }}>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                                Policy Engine Diagnostics:
                              </span>
                              <div style={{ fontSize: "0.8rem" }}>
                                <div style={{ marginBottom: "6px" }}>
                                  <span style={{ color: "var(--text-muted)" }}>Reason: </span>
                                  <span style={{ fontStyle: "italic" }}>"{trace.policy_reason}"</span>
                                </div>
                                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "8px" }}>
                                  {trace.cache_hit && <span className="badge badge-cache">Cache Hit</span>}
                                  {trace.fallback_triggered && <span className="badge badge-fallback">Fallback Triggered</span>}
                                  {trace.retries_attempted > 0 && <span className="badge badge-small_model">Retries: {trace.retries_attempted}</span>}
                                  {trace.circuit_breaker_tripped && <span className="badge badge-human_review">Circuit Breaker Tripped</span>}
                                </div>
                              </div>
                            </div>

                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
}
