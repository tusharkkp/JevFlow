# JevFlow Architecture Specification
## Adaptive AI Gateway Powered by System One Decisions

---

## 1. System Vision & Core Invariant

### 1.1 The Problem
In standard GenAI architectures, applications naively route every incoming user prompt directly to an expensive, high-latency frontier LLM (e.g., GPT-4o, Claude 3.5 Sonnet, Gemini Pro). 
- A simple greeting (`"Hello!"`) or straightforward factual query (`"What is the capital of France?"`) incurs the same latency (1000–3000ms) and cost as a complex architecture design question.
- Using prompt engineering on an LLM to "classify itself" adds more tokens, latency, and cost before the actual task is executed.

### 1.2 The System One Paradigm
Psychologist Daniel Kahneman described human cognition as two systems:
- **System 1:** Fast, automatic, subconscious, intuitive, pattern-matching.
- **System 2:** Slow, deliberate, logical, calculating, resource-intensive.

**Jev** (developed by TypeSafe) is built specifically as a **System One engine** for software: it returns fast, structured, calibrated probability distributions across discrete types (`noul`, `choice`, `score`) rather than generating unconstrained tokens.

### 1.3 The Core Architectural Invariant
> **Probabilistic Intelligence vs. Deterministic Enforcement**
> - **Jev = Probabilistic Intelligence:** Evaluates intent, estimates complexity, flags safety risks, and provides confidence scores.
> - **Policy Engine = Deterministic Enforcement:** Enforces business rules, budgets, safety gates, and routing rules in pure deterministic code.
> 
> *Jev never executes actions, security gates, or infrastructure calls directly. Application code always holds the final authority.*

---

## 2. End-to-End Request Pipeline

```
                                      CLIENT REQUEST
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │     API GATEWAY (FastAPI)     │
                             │  - Request ID & Timestamp    │
                             │  - Schema Validation         │
                             └──────────────┬───────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │       SECURITY & AUTH        │
                             │  - API Key Verification      │
                             │  - Rate Limiter (Token Bucket│
                             └──────────────┬───────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │         CACHE LOOKUP         │
                             │  - Exact & Semantic Hit?     │
                             └──────┬───────────────┬───────┘
                        Hit         │               │  Miss
                  ┌─────────────────┘               ▼
                  │                  ┌──────────────────────────────┐
                  │                  │     JEV DECISION LAYER       │
                  │                  │  - Intent (Choice)           │
                  │                  │  - Complexity (Score)        │
                  │                  │  - Safety (Noul)             │
                  │                  │  - Recommended Route (Choice)│
                  │                  └──────────────┬───────────────┘
                  │                                 │
                  │                                 ▼
                  │                  ┌──────────────────────────────┐
                  │                  │   DETERMINISTIC POLICY       │
                  │                  │  - Safety Gate (Reject/Review│
                  │                  │  - Confidence Thresholds     │
                  │                  │  - Latency / Cost Budgets    │
                  │                  │  - System Health & Outages   │
                  │                  └──────────────┬───────────────┘
                  │                                 │
                  │                                 ▼
                  │                  ┌──────────────────────────────┐
                  │                  │      EXECUTION ROUTING       │
                  │                  │ ├── Small/Cheap Provider     │
                  │                  │ ├── Frontier Provider        │
                  │                  │ ├── Rule/Deterministic       │
                  │                  │ └── Human Review / Fallback  │
                  │                  └──────────────┬───────────────┘
                  │                                 │
                  └─────────────────┬───────────────┘
                                    │
                                    ▼
                             ┌──────────────────────────────┐
                             │   OBSERVABILITY & TELEMETRY  │
                             │  - Latency (Jev, Model, Total│
                             │  - Cost Tracking             │
                             │  - Route Selection & Fallback│
                             │  - Persistence (PostgreSQL)  │
                             └──────────────┬───────────────┘
                                            │
                                            ▼
                                      CLIENT RESPONSE
```

---

## 3. Component Breakdown

### 3.1 API Gateway Core (`backend/app/api`)
- Built with Python 3.12 and FastAPI.
- Validates client payloads using Pydantic V2 models.
- Generates a unique `request_id` (UUIDv7 or UUIDv4) for distributed tracing.
- Captures start-to-finish timing checkpoints for P50, P95, and P99 metric computation.

### 3.2 Jev Decision Pipeline (`backend/app/jev`)
Issues targeted questions to `POST /v1/systemone` using the authenticated TypeSafe API:
1. **`intent` (`choice`)**: `factual_question`, `coding`, `summarization`, `reasoning`, `data_analysis`, `creative`, `other`.
2. **`complexity` (`score`)**: 
   - 0: Simple (trivial lookup, greeting, direct translation).
   - 1: Moderate (standard coding, multi-paragraph explanation).
   - 2: Complex (multi-step logical reasoning, architectural design, subtle edge cases).
3. **`safety` (`noul`)**: Probability that the request is safe to execute automatically without malicious intent or injection.
4. **`execution_route` (`choice`)**: Recommendation: `deterministic`, `small_model`, `frontier_model`, `human_review`.
5. **Confidence Evaluation**: Jev provides confidence scores for choices and score rubrics to assess uncertainty.

### 3.3 Deterministic Policy Engine (`backend/app/policy`)
The policy engine translates probabilistic signals and runtime state into binding execution plans:
- **Safety Rule:** If `safety_noul < 0.85` or prompt injection detected $\rightarrow$ Route to `review` or `reject`.
- **Cache Policy:** If prompt is deterministic and cacheable $\rightarrow$ Enable cache lookup and write-back.
- **Complexity & Confidence Rule:**
  - If `complexity <= 0.6` AND `confidence >= HIGH_CONFIDENCE_THRESHOLD` $\rightarrow$ `small_model`.
  - If `complexity > 1.2` OR `intent == "reasoning"` $\rightarrow$ `frontier_model`.
  - If `confidence < MEDIUM_CONFIDENCE_THRESHOLD` $\rightarrow$ Escalate to `frontier_model` or `fallback`.
- **Constraint Budget Rule:**
  - If `client_latency_budget < 500ms` $\rightarrow$ Clamp to fastest available model.
  - If `cost_budget < threshold` $\rightarrow$ Clamp to budget-friendly provider.

### 3.4 Model Provider Abstraction (`backend/app/providers`)
An extensible, provider-agnostic interface:
```python
class ModelProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse: ...
    
    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float: ...
    
    @abstractmethod
    async def health(self) -> ProviderHealth: ...
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...
```
Implementations:
- `MockProvider`: Fast, deterministic local mock for testing without API costs.
- `SmallModelProvider`: Fast/cheap models (e.g., Llama-3.2-3B, Claude 3.5 Haiku, GPT-4o-mini).
- `FrontierModelProvider`: High-capability models (e.g., Claude 3.5 Sonnet, GPT-4o).
- `DeterministicProvider`: Instant zero-cost responses for static intents (e.g., greetings, ping).

### 3.5 Reliability & Fallback Engine
- **Jev Circuit Breaker / Timeout:** If Jev takes $>1500\text{ms}$ or returns a 5xx error, degrade gracefully to a deterministic rule-based heuristic routing layer rather than failing the client request.
- **Provider Failover:** If the selected primary provider fails or times out, fail over to the secondary/fallback provider.
- **Telemetry Recording:** Every fallback event is stamped with `fallback: true` and the fallback reason (`jev_timeout`, `provider_5xx`, `low_confidence`).

### 3.6 Observability & Telemetry Engine (`backend/app/telemetry`)
Structured JSON logging and database persistence:
- `request_id`, `timestamp`
- `intent`, `complexity_score`, `jev_confidence`, `safety_score`
- `selected_route`, `actual_model`, `cache_hit`
- `jev_latency_ms`, `model_latency_ms`, `gateway_overhead_ms`, `total_latency_ms`
- `input_tokens`, `output_tokens`, `estimated_cost_usd`
- `baseline_cost_usd` (what it would have cost if routed directly to frontier)
- `cost_saved_usd`
- `fallback_triggered`, `fallback_reason`

### 3.7 Evaluation & Benchmark Engine (`backend/app/experiments`)
Allows automated A/B evaluation across a curated dataset:
- **Baseline Strategy:** Route 100% of requests to `FrontierModelProvider`.
- **Rule-Based Strategy:** Route using static keyword/regex heuristic rules.
- **JevFlow Strategy:** Route using Jev System One decision + Policy Engine.
- **Comparative Metrics:**
  - P50, P95, P99 Latency
  - Total and Average Cost per Request
  - Cost Reduction % vs Baseline
  - Task Success Rate / Escalation Rate
  - Fallback Frequency

### 3.8 Engineering Observability Dashboard (`frontend/`)
Next.js dashboard featuring:
- **System Overview:** Live P50/P95 latency, cost/request, fallback rate, total requests.
- **Routing Distribution:** Breakdown of execution routes (deterministic, small, frontier, review).
- **Confidence Matrix:** Scatter plot and histogram of Jev confidence vs. routing escalation.
- **Request Traces:** Step-by-step waterfall trace for individual requests.
- **Benchmark / Experiment Studio:** Run experiments, view comparative tables and cost-savings curves.

---

## 4. Architectural Decision Records (ADRs)

### ADR-01: FastAPI for Gateway Backend
- **Context:** Need an asynchronous, type-safe, high-concurrency API server with automatic OpenAPI documentation.
- **Decision:** Python 3.12 with FastAPI and Pydantic V2.
- **Consequences:** Native async I/O handles concurrent Jev queries and provider streaming with minimal overhead. Pydantic guarantees runtime contract safety.

### ADR-02: Decoupled Decision & Policy Layers
- **Context:** Should Jev directly pick the exact model and provider?
- **Decision:** No. Jev provides probabilistic classification and scores. The Policy Engine runs deterministic Python logic against business configurations.
- **Consequences:** Enables instant policy adjustments without retraining or re-prompting; preserves deterministic security guarantees.

### ADR-03: Provider Abstraction with Mock-First Development
- **Context:** Avoid burning real API credits during core pipeline and test suite development.
- **Decision:** Build an abstract `ModelProvider` base class with a configurable `MockProvider`.
- **Consequences:** High test velocity, 100% offline unit/integration test capability, zero external spend during initial phases.

---

## 5. Development Roadmap Overview

| Phase | Milestone | Focus |
|---|---|---|
| **Phase 0** | Architecture & Contract Verification | OpenAPI schema, design documents, environment templates *(Current)* |
| **Phase 1** | Minimal Gateway Skeleton | FastAPI server, mock decision layer, mock provider, basic request trace |
| **Phase 2** | Real TypeSafe Jev Integration | Live `/v1/systemone` integration, typed models, error handling |
| **Phase 3** | Model Provider Layer | Unified multi-provider abstraction, token & cost calculation |
| **Phase 4** | Adaptive Policy Engine | Multi-factor routing (confidence, latency budget, complexity, cost) |
| **Phase 5** | Reliability & Fault Tolerance | Circuit breakers, timeouts, failover chains, fallback telemetry |
| **Phase 6** | Caching & Rate Limiting | Redis cache and token bucket rate limiter |
| **Phase 7** | Telemetry & Observability | PostgreSQL persistence, metric aggregation, trace explorer |
| **Phase 8** | Evaluation & Benchmarking | Dataset runner, A/B experiment harness, statistical comparisons |
| **Phase 9** | Next.js Engineering Dashboard | Live real-time visualization of routes, latency percentiles, and cost savings |
