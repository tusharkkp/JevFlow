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

---

## Entry 2: Phase 2 — Real TypeSafe Jev Integration & Multi-Question Schema Transformation

- **Concept:** Multi-Question System One API integration (`POST /v1/systemone`) and resilient fault-tolerant client design.
- **Why it exists:** To replace or wrap our mock decision engine with the live TypeSafe Jev System One service. Rather than treating an AI model as an open-ended conversational bot, Jev is used as a fast, typed probabilistic classifier that answers multiple orthogonal questions about a shared `state` simultaneously.
- **How we implemented it:**
  - *Client (`backend/app/jev/client.py`):* Built `TypeSafeJevClient` utilizing asynchronous HTTP (`httpx`) adhering to the official OpenAPI 3.1 specification. Implemented typed exceptions (`TypeSafeAuthError`, `TypeSafeValidationError`, `TypeSafeTimeoutError`, `TypeSafeAPIError`) with custom HTTP client injection for testing.
  - *Multi-Question Query Construction (`backend/app/decision/jev_engine.py`):* Formulated 4 simultaneous questions in a single request:
    1. `intent` (`choice`): Categorizes into 6 discrete buckets with human-interpretable criteria descriptions.
    2. `complexity` (`score`): Evaluates on a 3-level rubric (Simple, Moderate, Complex), returning an expected score between 0.0 and 2.0.
    3. `safety` (`noul`): Binary probability of safety ($0.0 \dots 1.0$).
    4. `execution_route` (`choice`): Recommended execution tier.
  - *Graceful Degradation:* Wrapped network execution with try/except blocks. If `TYPESAFE_API_KEY` is not present, or if Jev times out ($>1500\text{ms}$) or returns 5xx, the engine automatically falls back to `MockDecisionEngine` and records the fallback cause in telemetry without dropping the user's request.
- **Alternative approaches:**
  - *Sequential Single-Question Calls:* Sending four individual HTTP requests for intent, complexity, safety, and route. (Trade-off: Would multiply network latency by 4x. Sending a single multi-question payload evaluates all 4 concurrently on the TypeSafe cluster in one round-trip).
  - *Crash on Missing API Key:* Halting the server if `TYPESAFE_API_KEY` is not set. (Trade-off: Prevents offline development, CI/CD testing, and causes total gateway downtime during third-party API outages).
- **Trade-offs:** Combining 4 questions into one payload makes the request JSON larger (~1.2 KB), but this is negligible compared to the massive latency reduction of a single round-trip.
- **What I learned:** Jev's `ScoreQuestion` returns an expected value as a continuous float (e.g. 1.65) calculated as a probability-weighted average across rubric levels. This allows our policy engine to evaluate fine-grained thresholds (e.g., $score > 1.4$) rather than coarse discrete buckets.
- **What could fail:** If TypeSafe updates rubric criteria or return structures in a future API version, Pydantic schema validation would catch the deviation, triggering our fallback engine safely.


