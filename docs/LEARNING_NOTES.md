# JevFlow Learning Notes & Engineering Journal

---

## Entry 0: Phase 0 — System One Decisions & The Architecture of an Adaptive Gateway

- **Concept:** System One Probabilistic Decision Layer vs. Deterministic Policy Enforcement.
- **Why it exists:** Standard AI applications typically suffer from the "Hammer and Nail" syndrome: every incoming prompt—regardless of simplicity, risk, or required capability—is forwarded directly to an expensive, high-latency frontier model (System Two generation). Using a general LLM to route itself creates extra latency, token usage, and unpredictability. System One models (such as TypeSafe Jev) provide fast, structured, calibrated probability distributions across discrete questions (`noul`, `choice`, `score`).
- **How we implemented it:** We inspected the official TypeSafe OpenAPI 3.1 schema directly at `https://api.typesafe.ai/openapi.json`. We designed an architectural pipeline where Jev evaluates four orthogonal dimensions (`intent`, `complexity`, `safety`, `execution_route`), and a separate deterministic Policy Engine evaluates thresholds, budgets, and failovers before dispatching the request to the execution provider.
- **Alternative approaches:**
  1. *Direct Prompt-based Classification:* Use an LLM like GPT-4o-mini with structured output JSON to classify queries. (Drawback: Adds 500–1200ms latency and high token overhead per request).
  2. *Static Keyword / Regex Rules:* Use string matching. (Drawback: Extremely brittle, cannot assess semantic nuance, tone, or disguised complexity).
  3. *Embedding Vector Similarity:* Embed queries and run cosine similarity against reference intent clusters. (Drawback: Does not provide calibrated confidence or rubric scoring on cognitive complexity).
- **Trade-offs:** Jev introduces an extra network hop before execution. If Jev latency is 50–150ms, it is only a net win if it successfully routes a significant portion of queries away from slow frontier models (1000–3000ms) to fast small models, cached responses, or deterministic logic, or if it catches security and safety risks before execution.
- **What I learned:** In TypeSafe's API contract, a single `POST /v1/systemone` request accepts multiple heterogeneous questions (`noul`, `choice`, `score`) evaluated against a shared `state` object. Output tokens are currently free of charge, and answers arrive keyed by the user-defined question names with explicit probability distributions.
- **What could fail:** If Jev becomes unavailable or experiences network latency spikes, the gateway could become a bottleneck unless a strict timeout (e.g., 1500ms) with a deterministic fallback heuristic is implemented.

---

## Entry 1: Phase 1 — Minimal Gateway Skeleton & The Decision-Policy Pipeline

- **Concept:** End-to-end request orchestration and strict separation between probabilistic decision output and deterministic policy enforcement.
- **Why it exists:** Before integrating live external network APIs (TypeSafe Jev, frontier LLMs), we need a verified software contract. The gateway must be able to take an incoming request, assign distributed tracing metadata (`request_id`, timestamps), consult a decision engine, evaluate a deterministic policy, execute against a provider, and compute complete latency and cost telemetry without external dependencies.
- **How we implemented it:**
  - *Schemas (`backend/app/schemas`):* Defined strongly-typed models using Pydantic V2 (`GatewayRequest`, `DecisionResult`, `ExecutionPlan`, `GatewayResponse`, `TelemetryTrace`).
  - *Decision Layer (`backend/app/decision`):* Defined an abstract `DecisionEngine` base class and a `MockDecisionEngine` producing calibrated distributions for intent, complexity score (0.0 to 2.0), safety probability, and confidence.
  - *Policy Engine (`backend/app/policy`):* Pure Python business logic evaluating safety gates, client latency budget limits, low-confidence escalation, and complexity rules into an immutable `ExecutionPlan`.
  - *Provider Abstraction (`backend/app/providers`):* Defined `ModelProvider` base class and `MockModelProvider` simulating deterministic, small, and frontier model responses with realistic token usage and cost accounting ($0.25/$1.25 per 1M tokens for small, $3.00/$15.00 for frontier).
  - *Gateway Service (`backend/app/services`):* Assembled the pipeline, calculated true gateway overhead (`total_latency_ms - decision_latency_ms - provider_latency_ms`), baseline costs, and net cost savings.
- **Alternative approaches:**
  - *Coupled Monolithic Handler:* Placing classification, business rules, and LLM calls in a single FastAPI route function. (Drawback: Impossible to unit test independently, impossible to mock Jev, and violates Single Responsibility Principle).
  - *Letting the Decision Engine Pick the Model Directly:* Letting the AI model return `"gpt-4o"` or `"haiku"`. (Drawback: AI has no runtime awareness of client latency budgets, provider outages, or account cost constraints; security risks cannot be deterministically blocked).
- **Trade-offs:** We introduced abstractions (`DecisionEngine`, `ModelProvider`, `PolicyEngine`) which creates more files upfront. However, this decouples third-party API dependencies completely, allowing 9 tests to run and pass in 70 milliseconds without internet or API keys.
- **What I learned:** Keeping the policy engine purely functional (input `DecisionResult` + constraints $\rightarrow$ output `ExecutionPlan`) makes testing edge cases like low-confidence escalation and latency budget clamping trivial and deterministic.
- **What could fail:** In-memory mock providers cannot reveal network jitter, partial response timeouts, or HTTP 422 schema validation mismatches that real APIs will exhibit in Phase 2.

