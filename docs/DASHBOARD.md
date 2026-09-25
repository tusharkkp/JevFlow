# JevFlow Observability & Evaluation Dashboard

## 1. Overview

The **JevFlow Dashboard** is an engineering-grade web application built with **Next.js (App Router, TypeScript, Vanilla CSS)** providing real-time visibility into the System One decision layer, deterministic policy engine, model provider executions, and comparative A/B benchmarks.

---

## 2. Dashboard Components

### 2.1 System Health Bar & Perimeter Status
Located at the top of the dashboard, displaying live status for:
- **Gateway Health:** Online/offline status and active API version.
- **Decision Engine:** Current active engine (`TypeSafe Jev` or offline calibrated fallback).
- **Cache Store:** Active memory/Redis cache capacity and current entry count.
- **Rate Limiter:** Token bucket fill rate and capacity.
- **Manual Sync:** Instant refresh button with auto-refresh every 10 seconds.

### 2.2 KPI Metrics & Fleet Accounting
- **Total Requests Evaluated:** Cumulative request count processed by the gateway.
- **Net Cost Saved ($):** Counter-factual dollar savings compared to sending 100% of traffic to Frontier models.
- **Cost Reduction Percentage (%):** Relative efficiency gain.
- **Median Latency (P50):** 50th percentile response time.
- **Tail Latency (P95 / P99):** Real-time monitoring of long-tail latency outliers.
- **Traffic Route Allocation:** Visual multi-segment bar breaking down traffic across:
  - `deterministic` (Emerald)
  - `cache` (Cyan)
  - `small_model` (Amber)
  - `frontier_model` (Purple)
  - `human_review` (Rose)
  - `fallback` (Red)

### 2.3 Interactive Routing Playground
An interactive sandbox for testing arbitrary prompts or preloaded archetypes:
- **Preloaded Presets:**
  - Simple Fact $\rightarrow$ Small Model
  - Greeting $\rightarrow$ Deterministic
  - Boilerplate Code $\rightarrow$ Small Model
  - Deep Reasoning $\rightarrow$ Frontier Model
  - Prompt Injection $\rightarrow$ Human Review
- **Constraint Controls:** Set custom client-side latency budgets (ms) or cost budgets ($).
- **Flamegraph / Waterfall Timeline:** Displays the exact millisecond duration of each phase:
  $$\text{Total Latency} = \text{Jev Decision} + \text{Model Execution} + \text{Gateway Overhead}$$
- **Policy Enforcement Rationale:** View why the policy engine chose, escalated, or clamped the route.

### 2.4 Trace Explorer & Distributed Spans
- Filterable table by route tier.
- Click to expand any historical trace to inspect the complete sub-millisecond waterfall breakdown, token accounting, and policy flags.

### 2.5 Empirical A/B Benchmark Matrix
- One-click trigger to execute the 3-way evaluation harness.
- Side-by-side comparison table validating:
  - Baseline (100% Frontier)
  - Strategy A (Static Rules)
  - Strategy B (JevFlow Adaptive)

---

## 3. How to Run the Dashboard

### 1. Start the Backend Gateway (FastAPI)
```powershell
$env:PYTHONPATH="."
.venv\Scripts\uvicorn backend.app.main:app --port 8000 --reload
```

### 2. Start the Frontend Dashboard (Next.js)
```powershell
cd frontend
npm run dev
```

Open your browser to `http://localhost:3000`.
