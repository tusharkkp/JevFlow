# Deterministic Policy Engine & Adaptive Routing Specification

---

## 1. System Invariant & Core Mandate

In JevFlow:
> **Jev provides Probabilistic Intelligence.**  
> **The Policy Engine provides Deterministic Enforcement.**

The Policy Engine is a pure, predictable state machine written in application code. It translates uncertain, multi-dimensional probabilistic signals from System One into a concrete, legally binding [`ExecutionPlan`](file:///c:/PROJECTS/New%20folder/backend/app/policy/engine.py#L9).

$$\text{Plan} = \text{Policy}\Big(\text{Jev Decision}, \;\text{Client Budgets}, \;\text{Runtime System State}\Big)$$

---

## 2. Dynamic Inputs to the Policy Engine

Rather than static routing ($Request \rightarrow Model$), JevFlow evaluates 4 input vectors:

1. **System One Decision Vector (`DecisionResult`):**
   - Categorical `intent` (`factual_question`, `coding`, `reasoning`, etc.)
   - Expected continuous `complexity_score` ($0.0 \dots 2.0$)
   - Calibrated `safety_probability` ($0.0 \dots 1.0$)
   - Classification `confidence` ($0.0 \dots 1.0$)
   - Recommended initial route
2. **Client Request Constraints:**
   - Strict `latency_budget_ms` (e.g. interactive UI requiring $<400\text{ms}$)
   - Strict `cost_budget` (e.g. bulk batch query capped at $\$0.001$)
   - Estimated input token volume
3. **Runtime System Conditions (`SystemState`):**
   - In-flight concurrent requests count & `load_ratio`
   - Provider availability (`healthy`, `degraded`, `unavailable`)
   - Real-time observed P50/P95 latencies per route
   - Cache availability flag

---

## 3. The 8 Evaluation Gates (Ordered by Priority)

The Policy Engine evaluates gates sequentially. The first gate to trigger short-circuits the pipeline with a documented rationale:

```
[ Incoming Request + Jev Decision + System State ]
                        │
                        ▼
   1. Safety Gate ────────────────────────► Unsafe? ──► [Human Review / Quarantine]
                        │ Safe
                        ▼
   2. Provider Outage Gate ───────────────► Frontier Down? ──► [Downgrade to Small Model]
                        │ Available
                        ▼
   3. Load-Shedding Gate ────────────────► Load > 80%? ──► [Shed Load to Small Model]
                        │ Normal
                        ▼
   4. Latency Budget Gate ───────────────► Budget < Expected Frontier? ──► [Force Fast Model]
                        │ Within Budget
                        ▼
   5. Cost Budget Gate ──────────────────► Budget < Expected Cost? ──► [Clamp to Cheap Model]
                        │ Affordable
                        ▼
   6. Confidence Escalation Gate ────────► Conf < 0.60? ──► [Escalate to Frontier]
                        │ Confident
                        ▼
   7. Complexity & Intent Gate ──────────► Complex/Reasoning? ──► [Frontier Model]
                        │ Moderate/Simple
                        ▼
   8. Default Recommendation ────────────► [Selected Execution Route]
```

### Detailed Gate Specifications

| Priority | Gate Name | Trigger Condition | Deterministic Action |
|---|---|---|---|
| **1** | **Safety Gate** | `safety_probability < 0.80` or `not is_safe` | Route to `HUMAN_REVIEW` (quarantine). Never execute against downstream LLMs. |
| **2** | **Provider Health** | Target provider status == `"unavailable"` | Automatic failover to `SMALL_MODEL` or `DETERMINISTIC`. |
| **3** | **Load Shedding** | `system_load_ratio >= HIGH_LOAD_THRESHOLD` (80%) | Reroute non-critical requests from Frontier to `SMALL_MODEL` to preserve gateway throughput. |
| **4** | **Latency Budget** | `latency_budget_ms < (decision_latency + observed_frontier_latency)` | Force `SMALL_MODEL` or `DETERMINISTIC` regardless of theoretical complexity. |
| **5** | **Cost Budget** | `cost_budget < estimated_frontier_cost` | Clamp execution to `SMALL_MODEL` to guarantee SLA spend limits. |
| **6** | **Low-Confidence Escalation** | `confidence < MEDIUM_CONFIDENCE_THRESHOLD` (0.60) | Escalate to `FRONTIER_MODEL` for cognitive safety and higher reasoning accuracy. |
| **7** | **Complexity & Intent** | `complexity_score <= 0.3` & `confidence >= 0.85`<br>`complexity_score >= 1.4` or `intent == "reasoning"` | Direct to `DETERMINISTIC` / `SMALL_MODEL`<br>Direct to `FRONTIER_MODEL`. |
| **8** | **Default Route** | Unambiguous standard classification | Mapped to recommendation with verified health. |

---

## 4. Configuration Schema

All thresholds are centralized in [`backend/app/core/config.py`](file:///c:/PROJECTS/New%20folder/backend/app/core/config.py) and configurable via environment variables without code modification:

```env
HIGH_CONFIDENCE_THRESHOLD=0.85
MEDIUM_CONFIDENCE_THRESHOLD=0.60
HIGH_LOAD_THRESHOLD=0.80
MAX_CONCURRENCY=100
MAX_LATENCY_BUDGET_MS=2000
MAX_COST_PER_REQUEST=0.05
ENABLE_HUMAN_REVIEW=true
ENABLE_CACHE=true
```
