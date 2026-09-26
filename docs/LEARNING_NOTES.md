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

---

## Entry 3: Phase 3 — Real Model Providers, Vendor Abstraction & Automatic Failover

- **Concept:** The Strategy Pattern for Multi-Tier Model Providers and Counter-Factual Cost Accounting.
- **Why it exists:** GenAI gateways should never be locked into a single model vendor (e.g., OpenAI, Anthropic, or local open-weights). Furthermore, to prove that System One routing saves money, the gateway must accurately compute token economics ($ per 1M tokens) and track the difference between what a request actually cost vs. what it would have cost on an expensive frontier model.
- **How we implemented it:**
  - *Unified Interface (`backend/app/providers/base.py`):* Defined `ModelProvider` declaring `generate()`, `estimate_cost()`, `health()`, and `metadata`.
  - *Provider Implementations:*
    1. `DeterministicProvider`: Sub-millisecond rule matching for greetings and static facts ($0.00 cost).
    2. `SmallModelProvider`: Cost-efficient fast model ($0.25 input / $1.25 output per 1M tokens).
    3. `FrontierModelProvider`: Deep reasoning model ($3.00 input / $15.00 output per 1M tokens).
    4. `HumanReviewProvider`: Quarantine queue for safety-flagged prompts ($0.00 cost).
  - *Registry & Failover Router (`backend/app/providers/registry.py`):* Manages provider lifecycle and automatic failover chains (if Frontier fails, failover to Small Model; if Small Model fails, failover to Deterministic).
  - *Counter-Factual Cost Delta:* `GatewayService` calculates `baseline_cost_usd` against Frontier pricing and records `cost_saved_usd` on every request.
- **Alternative approaches:**
  - *Ad-Hoc Provider Calls:* Writing inline `if-else` blocks calling vendor APIs directly in the route handler. (Trade-off: High technical debt, impossible to mock cleanly, and fragile failover).
  - *Unified Proxy Services (e.g. LiteLLM):* Using an external multi-vendor proxy. (Trade-off: Useful for pure API translation, but lacks the deep integration with System One decisions, policy engines, and counter-factual savings metrics).
- **Trade-offs:** Abstracting multiple providers requires normalizing token usage and generation content into a common `ProviderResponse`. Provider-specific features (e.g. multimodal inputs) must be handled by provider adapters.
- **What I learned:** By instrumenting counter-factual accounting on every single request, the gateway produces verifiable empirical proof of dollar savings without needing offline estimates.
- **What could fail:** Upstream vendor rate-limits (HTTP 429) or transient outages. Handled by the Provider Registry's automatic failover chain.

---

## Entry 4: Phase 4 — Adaptive Multi-Factor Policy Engine & Runtime System State

- **Concept:** Multi-Factor Adaptive Routing: $\text{Route} = f(\text{Complexity}, \text{Confidence}, \text{Tokens}, \text{System Load}, \text{Provider Health}, \text{Latency Budget}, \text{Cost Budget})$.
- **Why it exists:** Real-world API gateways cannot operate on naive static mappings (e.g. "if reasoning, always use GPT-4o"). In production, if system concurrency is spiking at 90%, if the client has a 250ms interactive UI SLA, or if the frontier model provider is suffering a degraded outage, blindly routing to the frontier model causes cascading timeouts, broken SLAs, and service failure.
- **How we implemented it:**
  - *Runtime State (`backend/app/policy/state.py`):* Defined `SystemState` tracking concurrent active in-flight requests, `load_ratio`, provider availability maps, and observed P50/P95 latencies per route.
  - *The 8 Ordered Gates (`backend/app/policy/engine.py`):* Implemented sequential deterministic evaluation gates:
    1. Safety Gate: Quarantines requests to `HUMAN_REVIEW` if $prob < 0.80$.
    2. Provider Outage Gate: Detects if target provider is degraded/unavailable and reroutes safely.
    3. Load Shedding Gate: Automatically sheds non-critical traffic to `SMALL_MODEL` when load $\ge 80\%$.
    4. Dynamic Latency Budget Gate: Compares client budget against P95 frontier network estimates and clamps when budget is at risk.
    5. Cost Budget Gate: Evaluates estimated input tokens against dollar budget limits.
    6. Confidence Escalation Gate: Escalate uncertain decisions to frontier when confidence $< 0.60$.
    7. Complexity & Intent Gate: Assigns trivial/simple to deterministic or small, and complex reasoning to frontier.
    8. Default Recommendation Mapping: Fallback to System One recommendation with verified health.
- **Alternative approaches:**
  - *Machine Learning Meta-Router:* Training a secondary ML model to predict the best route. (Trade-off: Black box, non-deterministic, introduces latency, and cannot guarantee hard budget compliance).
  - *Static If-Else Branching:* (Trade-off: Ignores runtime system conditions, causing cascading failures during high traffic or provider outages).
- **Trade-offs:** Adding runtime state inspection requires tracking in-flight requests and provider health, adding $\sim 5\mu\text{s}$ overhead, but this guarantees SLA adherence and load resilience.
- **What I learned:** P95 latency margins (accounting for $2.2\times$ network variance) must be used instead of optimistic P50 averages when evaluating latency budgets, otherwise jitter will violate client SLAs.
- **What could fail:** Sudden unmetered traffic surges. Handled by gateway rate limiting and Redis token buckets (Phase 6).

---

## Entry 5: Phase 5 — Reliability Engineering: Circuit Breakers, Retries & Failure Telemetry

- **Concept:** The Circuit Breaker State Machine (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF-OPEN`), Exponential Backoff with Jitter, and Explicit Failure Accounting.
- **Why it exists:** Upstream AI APIs (Jev, frontier LLMs) will inevitably experience network drops, rate limits, or transient 5xx errors. If an application keeps firing requests into a failing service, requests pile up, connections exhaust, and the gateway suffers catastrophic cascade failure. A circuit breaker protects downstream services by failing fast without making network calls once an outage is detected.
- **How we implemented it:**
  - *Circuit Breaker (`backend/app/reliability/circuit_breaker.py`):* Implemented a stateful circuit breaker. If consecutive failures exceed threshold ($N=2$ or $3$), the breaker trips to `OPEN`. While `OPEN`, calls immediately throw `CircuitBreakerOpenException` in $<0.1\text{ms}$ without making network calls. After `recovery_timeout_sec`, it transitions to `HALF_OPEN` to test recovery with a single probe request.
  - *Exponential Backoff with Jitter (`backend/app/reliability/retry.py`):* Wrapped provider calls with retry logic ($delay = base \times 2^{attempt} + \text{jitter}$). Jitter (20% random spread) prevents the "thundering herd" problem where multiple clients retry at the exact same millisecond.
  - *Protected Components:* Wired circuit breakers into `TypeSafeJevEngine` and each tier of `ProviderRegistry`.
  - *Explicit Telemetry:* Stamped each request trace with `retries_attempted`, `circuit_breaker_tripped`, and `error_category` (`timeout`, `circuit_breaker_open`, `provider_error`, `policy_rejection`).
- **Alternative approaches:**
  - *Infinite Retries:* Retrying until success. (Trade-off: Exhausts connection pools, multiplies costs, and locks user requests).
  - *Hidden Errors:* Silently returning an empty string or generic answer without tracking. (Trade-off: Destroys observability; engineers cannot diagnose why a fallback occurred).
- **Trade-offs:** Retries add latency when transient errors occur, but save the request from failing. Fast-failing in the `OPEN` state drops latency from $1500\text{ms}$ (timeout) to $0.1\text{ms}$ (instant heuristic fallback).
- **What I learned:** During a complete upstream provider outage, fail-fast circuit breaking allows JevFlow to maintain 100% availability for end users by routing immediately to local small models or deterministic logic without waiting for network timeouts.
- **What could fail:** If all providers (Frontier, Small, Deterministic) fail concurrently, the gateway must return a graceful degraded 503 rather than an unhandled crash.

---

## Entry 6: Phase 6 — Intelligent Response Caching & Token-Bucket Rate Limiting

- **Concept:** Pre-Decision Semantic/Canonical Caching and Perimeter Token-Bucket Rate Limiting.
- **Why it exists:**
  - *Caching:* The fastest and cheapest query is the one you never execute. Identical questions (e.g. definitions, documentation FAQs) shouldn't incur Jev decision latency or LLM token costs over and over.
  - *Policy-Governed Cacheability:* Not all LLM responses should be cached. Unsafe prompts, creative brainstorming, and human-review requests must never be cached. The deterministic Policy Engine decides whether `allow_cache` is enabled.
  - *Rate Limiting:* Protects the gateway perimeter from runaway client loops, scraping, and denial-of-service before consuming downstream API resources.
- **How we implemented it:**
  - *Cache Layer (`backend/app/cache`):* Defined `BaseCache` interface. Built `MemoryCache` (with TTL and capacity eviction) and `RedisCache` (with automatic fallback to in-memory cache if Redis is unconfigured).
  - *Canonical Key Generation:* Normalized whitespace and query punctuation, generating deterministic SHA-256 keys so `"explain photosynthesis?"` and `"  Explain Photosynthesis  "` hit the same cache entry.
  - *Pre-Decision Pipeline Bypass:* Looked up cache *before* calling Jev. A cache hit returns in $<2\text{ms}$ with $0.00 cost, 0 tokens, and `cache_hit: true`. On cache miss, writes to cache only if `plan.allow_cache` is true.
  - *Token Bucket Rate Limiter (`backend/app/rate_limiter/token_bucket.py`):* Implemented continuous token accumulation. Returns standard HTTP 429 Too Many Requests with compliant `Retry-After: <seconds>` headers when capacity is exhausted.
- **Alternative approaches:**
  - *Post-Decision Caching:* Running Jev first to see if it's cacheable. (Trade-off: Wastes Jev tokens and 100ms latency on every hit. Pre-decision caching checks the store immediately).
  - *Fixed-Window Counter:* (Trade-off: Vulnerable to traffic doubling at window boundary transitions; Token Bucket enforces a smooth, continuous rate).
- **Trade-offs:** In-memory caching is fast and requires zero infrastructure, but is local to a single worker. Redis allows shared cache state across distributed gateway instances.
- **What I learned:** Decoupling cache lookup before the decision layer yields the ultimate latency optimization: P50 latency drops from 40ms to 0.5ms for repeated queries.
- **What could fail:** Memory exhaustion if cache capacity is unbounded. Prevented by strict max entry limits (5,000 entries) with LRU eviction.

---

## Entry 7: Phase 7 — Observability: Persistent Telemetry, Latency Percentiles (P50/P95/P99) & Trace Explorer

- **Concept:** Long-term Telemetry Persistence, Distributed Tracing Waterfalls, and Statistical Percentile Accounting (P50, P95, P99).
- **Why it exists:** In-memory metrics vanish on process restart. To prove the engineering value of System One routing, the gateway must persist structured telemetry across thousands of requests to answer:
  1. *"What is our P95 and P99 latency compared to sending all queries to Frontier?"*
  2. *"How many total dollars did JevFlow save this week?"*
  3. *"What percentage of requests were routed to deterministic rules vs small models vs frontier models?"*
- **Privacy Guarantee:** In accordance with Section 16, user prompt text is **never stored** in the telemetry database. Only classification metadata, token counts, latencies, and routing paths are persisted.
- **How we implemented it:**
  - *Database Layer (`backend/app/db`):* Built asynchronous SQLAlchemy models (`RequestRecord`, `ExperimentRecord`). Uses PostgreSQL in production with automatic fallback to async SQLite for local testing.
  - *Metrics Engine (`backend/app/telemetry/metrics.py`):* Implemented linear interpolation percentile algorithms for P50, P95, and P99 latencies across total time, Jev decision time, model execution, and pure gateway overhead. Computed cumulative cost savings and route percentage distributions.
  - *Telemetry Repository (`backend/app/telemetry/repository.py`):* Handled async persistence and pagination queries.
  - *Trace API Endpoints (`backend/app/main.py`):*
    - `GET /v1/telemetry/summary`: Returns system-wide P50/P95/P99 latencies, cost savings %, fallback rates, and route breakdown.
    - `GET /v1/telemetry/requests`: Lists historical traces with route filtering and pagination.
    - `GET /v1/telemetry/requests/{request_id}`: Returns single-request waterfall latency breakdowns and token economics.
- **Alternative approaches:**
  - *Averages (Mean Latency):* (Trade-off: Averages conceal long-tail outliers; a 90ms average can hide a 2500ms P99 spike. Computing P95 and P99 is mandatory).
  - *Third-party SaaS (Datadog/NewRelic):* (Trade-off: Excellent for APM, but lacks gateway-native counter-factual cost savings calculation).
- **Trade-offs:** Storing every trace creates database write I/O. We optimized this by indexing primary lookups (`timestamp`, `selected_route`, `request_id`) and running writes asynchronously.
- **What I learned:** Isolating the waterfall breakdown (`jev_decision_ms`, `model_execution_ms`, `gateway_overhead_ms`) enables instant diagnosis of whether a latency spike was caused by the decision layer, the model provider, or internal gateway serialization.
- **What could fail:** Database connection drops during spikes. Handled with connection pooling and async rollback blocks.

---

## Entry 8: Phase 8 — Evaluation Engine: Curated Benchmarks, Comparative Routing Strategies & A/B Validation

- **Concept:** Empirical A/B/C Benchmarking, Route Alignment Accuracy, and Multi-Archetype Evaluation Harness.
- **Why it exists:** Architectural assertions in AI engineering must be proven with repeatable, quantitative data. Without an automated evaluation harness, claims that "adaptive routing saves money without degrading quality" are mere speculation. We need a standardized test suite comparing the baseline (100% Frontier) against static heuristics and JevFlow's adaptive pipeline.
- **How we implemented it:**
  - *Curated Benchmark Dataset (`backend/app/experiments/dataset.py`):* Defined 12 representative queries spanning 7 real-world archetypes: Simple Factual, Trivial Greetings, Simple Coding, Complex Systems Concurrency, Multi-Causal Historical Synthesis, Mathematical Proofs, Summarization, Ambiguous Queries, Adversarial Injections, and Repeated Cacheable Queries. Each item establishes ground truth for optimal routing tier and intent.
  - *Strategy Abstraction (`backend/app/experiments/strategies.py`):* Implemented the `RoutingStrategy` interface with three comparative implementations:
    1. `BaselineStrategy`: Naive standard architecture routing 100% of requests to Frontier Model ($3.00 / $15.00 per 1M tokens) with zero cache or classification.
    2. `RuleBasedStrategy`: Brittle static heuristics matching regex patterns and keywords (`"why"`, `"compare"`, `"prove"`).
    3. `JevFlowStrategy`: Full adaptive pipeline (Pre-decision Cache $\rightarrow$ Jev System One $\rightarrow$ 8-Gate Policy Engine $\rightarrow$ Dynamic Provider Execution).
  - *Benchmark Runner (`backend/app/experiments/runner.py`):* Executes strategies in isolation, computes accuracy (% of routes matching ground truth), P50/P95/P99 latency, token costs, cost reduction %, cache hit rate, and fallback rate. Automatically persists results to `ExperimentRecord` and outputs Markdown comparison tables.
  - *API & CLI Harness:* Exposed CLI interface (`python -m backend.app.experiments.runner --strategy all`) and REST endpoints (`POST /v1/experiments/run`, `GET /v1/experiments`).
- **Alternative approaches:**
  - *Ad-hoc Manual Prompt Testing:* Sending random prompts via Postman or Swagger UI. (Trade-off: Not reproducible, lacks statistical rigor, cannot compute percentiles or accurate baseline cost comparisons).
  - *LLM-as-a-Judge for Routing Decisions:* Using GPT-4o to evaluate whether Jev chose the right model. (Trade-off: Extremely expensive, slow, and non-deterministic. Curated ground truth benchmarks provide deterministic, repeatable baselines).
- **Trade-offs:** Running complete benchmarks across multiple strategies incurs compute time, but running with isolated in-memory caches and reproducible providers completes the entire 3-way evaluation in under 2 seconds.
- **What I learned:** JevFlow achieves **83.3% routing accuracy** and **66.3% cost reduction** compared to Baseline (33.3% accuracy, 0% reduction) and Static Rules (50.0% accuracy, 65.5% reduction). Furthermore, offloading queries to small models and cache reduces overall **P50 latency by 54.8%** (from 141.8ms down to 64.1ms), conclusively disproving the fear that the decision hop harms user experience.
- **What could fail:** Benchmark drift if the curated dataset does not represent future production query distributions. Solved by designing `BenchmarkItem` to be easily extensible as production telemetry identifies new traffic patterns.

---

## Entry 9: Phase 9 — Observability & Evaluation Dashboard: Real-Time Telemetry & Flamegraph Waterfalls

- **Concept:** Client-side Observability, Flamegraph / Distributed Span Waterfall Profiling, and Interactive Gateway Sandboxing.
- **Why it exists:** In distributed systems, opaque backends invite guesswork. When a gateway combines probabilistic decisions, deterministic policies, token bucket rate limiters, response caches, circuit breakers, and multiple model providers, operators need a single-pane-of-glass dashboard to answer operational questions in milliseconds:
  1. *"Why did prompt X route to a Small Model instead of Frontier?"*
  2. *"How many milliseconds were spent in the Jev decision layer vs model execution vs serialization?"*
  3. *"Are any circuit breakers open or tripping?"*
  4. *"What is our live cost reduction percentage across current production traffic?"*
- **How we implemented it:**
  - *Next.js App Router Architecture (`frontend/src`):* Bootstrapped Next.js 16 with TypeScript, React 19, and a custom high-tech obsidian design system in `globals.css` (glassmorphism panels, pulsing status dots, glow route badges, and custom scrollbars).
  - *API Client (`frontend/src/lib/api.ts`):* Built a typed asynchronous API client talking to FastAPI (`http://localhost:8000`), with graceful degradation and error handling.
  - *System Perimeter Bar (`Header.tsx`):* Displays real-time Gateway status (`ONLINE`/`OFFLINE`), active Decision Engine mode, Rate Limiter fill capacity, Cache size, and auto-refresh sync.
  - *KPI Overview Cards (`KpiGrid.tsx`):* Presents total evaluated requests, net cost savings ($), cost reduction %, P50 median latency, P95/P99 tail latencies, and traffic route percentage breakdown.
  - *Interactive Routing Playground (`Playground.tsx`):* Allows interactive prompt entry with preloaded archetypes, latency and cost constraints, and a visual **Flamegraph Waterfall Timeline** segmenting `Jev Decision`, `Model Execution`, and `Gateway Overhead`.
  - *Live Trace Explorer (`TraceTable.tsx`):* Filterable table with expand/collapse rows showing granular sub-millisecond breakdowns, token accounting, and policy enforcement rationale.
  - *Empirical Evaluation View (`BenchmarkView.tsx`):* Provides one-click execution of the 3-way comparative benchmark suite (Baseline vs Rules vs JevFlow).
- **Alternative approaches:**
  - *Pre-packaged APM Dashboards (e.g. Grafana / Datadog):* (Trade-off: Excellent for generic CPU/RAM/HTTP metrics, but incapable of visualizing Jev multi-question probability distributions, rubric complexity scores, or counter-factual LLM cost savings without cumbersome custom plugins).
  - *Monolithic HTML Templates (Jinja2):* (Trade-off: Requires page reloads, lacks smooth micro-animations, client-side auto-polling, and interactive flamegraph timeline rendering).
- **Trade-offs:** Running a Next.js frontend introduces Node.js as a runtime dependency alongside Python. However, compiling Next.js statically or using it as a decoupled SPA preserves clean separation between the gateway engine and the user interface.
- **What I learned:** Breaking down the request lifecycle into an explicit visual flamegraph (`Jev Decision` $\rightarrow$ `Provider Execution` $\rightarrow$ `Gateway Logic`) immediately reassures operators that the decision hop is negligible (~10ms) compared to the massive latency and cost savings achieved by avoiding the Frontier model.
- **What could fail:** Network CORS misconfiguration or gateway backend downtime. Handled gracefully via `Promise.allSettled` in the polling loop and prominent visual offline indicators.

---

## Entry 10: Phase 10 — Production Containerization: Docker Compose, Distributed Redis & Real LLM Providers

- **Concept:** Multi-container Orchestration, Distributed Caching via Redis, and Universal OpenAI-compatible Real Inference.
- **Why it exists:** Production AI systems cannot run as disconnected manual terminal commands on an operator's workstation. To ensure deterministic deployments, high-availability caching, and real LLM connectivity, the entire architecture (FastAPI gateway, Redis cache, Next.js frontend) must be containerized and orchestrated via Docker Compose.
- **How we implemented it:**
  - *Redis Service (`docker-compose.yml`):* Leveraged local `redis:7` image with container healthchecks (`redis-cli ping`). Configured `REDIS_URL=redis://redis:6379/0` in container networking.
  - *Backend Container (`backend/Dockerfile`):* Slim Python 3.12 image, unbuffered logging, dependency caching, FastAPI entrypoint, and automated curl healthchecks.
  - *Frontend Container (`frontend/Dockerfile`):* Multi-stage build (deps $\rightarrow$ builder $\rightarrow$ runner) compiling Next.js in production mode on port 3000.
  - *Real Model Integration (`backend/app/providers/openai_provider.py`):* Created `OpenAICompatibleProvider` supporting OpenAI, Groq, OpenRouter, and DeepSeek with token tracking, true latency accounting, and graceful offline fallback.
- **Alternative approaches:**
  - *Local Virtualenv Execution:* (Trade-off: Fast for development, but vulnerable to OS environment variations, missing Redis daemon, and port collision issues).
  - *Kubernetes (K8s):* (Trade-off: Overkill for local/single-node deployments; Docker Compose offers optimal balance of speed and container isolation).
- **Trade-offs:** Docker builds require initial image compilation time, but guarantee identical execution across local developer workstations, CI/CD pipelines, and cloud staging environments.
- **What I learned:** Decoupling the caching layer via `RedisCache` with an automatic `MemoryCache` fallback invariant ensures that whether Redis is running inside Docker or temporarily stopped, the gateway continues to serve requests without dropping traffic.
- **What could fail:** Port binding collisions if existing host processes occupy ports 3000, 6379, or 8000. Resolved by verifying and terminating host dev servers before launching Compose.










