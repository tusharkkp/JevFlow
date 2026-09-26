# JevFlow — Adaptive AI Gateway
### High-Performance LLM Routing Powered by System One Decisions & Deterministic Policy Enforcement

<p align="center">
  <a href="https://github.com/tusharkkp/JevFlow/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License: MIT" />
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+" />
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  </a>
  <a href="https://nextjs.org/">
    <img src="https://img.shields.io/badge/Next.js-16%20App%20Router-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 16" />
  </a>
  <a href="https://redis.io/">
    <img src="https://img.shields.io/badge/Redis-7%20Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis 7" />
  </a>
  <a href="https://www.docker.com/">
    <img src="https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose" />
  </a>
  <a href="https://pytest.org/">
    <img src="https://img.shields.io/badge/Tests-49%20Passing-success?style=for-the-badge&logo=pytest&logoColor=white" alt="49 Passing Tests" />
  </a>
</p>

---

## 📌 Executive Summary

**JevFlow** is an enterprise-grade, educational AI Gateway engineered to resolve the fundamental efficiency challenge of modern generative AI: **the "Hammer and Nail" syndrome**.

In standard production architectures, up to **80% of incoming user prompts** (trivial greetings, boilerplate code snippets, straightforward factual lookups, and duplicated queries) are routed directly to slow, expensive **Frontier Models** (e.g. GPT-4o, Claude 3.5 Sonnet) costing upwards of **$15.00 – $30.00 per million tokens**.

JevFlow deploys a dual-system cognitive architecture:
1. **System One Layer (Probabilistic Intelligence):** Powered by ultra-fast decision models (such as **TypeSafe Jev**), classifying prompt intent, scoring cognitive complexity ($0.0 \dots 2.0$), and calculating safety probabilities in **~10ms**.
2. **Deterministic Policy Engine (Hard Verification):** Enforces strict mathematical rules—budget clamping, safety firewalls, dynamic latency budgets with P95 safety margins, and circuit breaker failover—before any token is generated.

> 📊 **Empirical Result:** In controlled 12-archetype comparative benchmarking, JevFlow achieved **83.3% optimal route alignment**, slashed token expenditure by **66.3%**, and cut median end-to-end user latency (P50) by **54.8%** (from 141.8ms down to 64.1ms).

---

## 💥 The Problem Statement

| Failure Mode in Traditional Gateways | Real-World Impact | How JevFlow Solves It |
|---|---|---|
| **Universal Frontier Dispatch** | Burning enterprise budget on prompts like *"Hello"* or *"How do I sort a list?"* | Routes trivial prompts to $0.00 deterministic handlers or $0.15/M small models. |
| **Brittle Keyword Heuristics** | Regex rules fail on nuance (e.g. matching both a 5-line palindrome script and a lock-free ring buffer). | Uses multi-dimensional continuous rubric scoring ($0.0 \dots 2.0$) calibrated on semantic complexity. |
| **SLA & Latency Budget Breaches** | Sending time-sensitive queries to high-latency reasoning models under heavy load. | Dynamically clamps execution to small models when P95 model latency exceeds client SLA budgets. |
| **Adversarial Prompt Injections** | Complex jailbreaks slip past keyword filters and exploit frontier model capabilities. | Dedicated probabilistic safety gate intercepts malicious injections and re-routes to human review. |
| **Cache Redundancy** | Re-generating identical deterministic outputs burns thousands of dollars daily. | Canonical SHA-256 pre-decision cache lookup returning responses in **< 1ms** at **$0.00** cost. |

---

## 🚀 Key Features

### 🧠 1. System One Probabilistic Decision Layer
- **Multi-Question Vector Evaluation:** Dispatches 4 concurrent questions in a single round-trip: `intent` (choice), `complexity` (3-level continuous rubric score $0.0 \dots 2.0$), `safety` (probability $0.0 \dots 1.0$), and `execution_route` (tier recommendation).
- **Graceful Fallback Invariant:** If the external decision API is unreachable or times out (>1500ms), JevFlow instantly falls back to an internal calibrated engine without dropping the user request.

### 🛡️ 2. Deterministic 8-Gate Policy Engine
- **Safety Quarantine:** Deterministically flags unsafe prompts for human review regardless of model preference.
- **Dynamic Latency Budgeting:** Compares client SLAs against running P95 provider latencies with a $2.2\times$ safety margin.
- **Token-Aware Cost Budgeting:** Pre-calculates worst-case token costs and caps execution if cost budgets are exceeded.
- **Load Shedding:** Automatically sheds 80% of low-priority traffic to fast fallback tiers when gateway concurrency spikes.
- **Low-Confidence Escalation:** Auto-escalates ambiguous queries ($confidence < 0.60$) to frontier models when providers are healthy.

### ⚡ 3. High-Throughput Perimeter & Distributed Caching
- **Token Bucket Rate Limiting:** Enforces continuous quota accumulation, returning HTTP 429 with compliant `Retry-After` headers.
- **Canonical SHA-256 Caching:** Punctuation-normalized and whitespace-trimmed prompt hashing.
- **Dual-Tier Cache:** Seamless distributed **Redis Cache** with transparent, zero-downtime fallback to local in-memory LRU cache.

### 🔄 4. Universal Provider Abstraction & OpenRouter Integration
- **Universal OpenAI-Compatible Client:** Native support for **OpenRouter**, **OpenAI (GPT-4o / GPT-4o-mini)**, **Groq**, **DeepSeek**, and local **Ollama** models.
- **Four Execution Tiers:**
  - `DETERMINISTIC`: Static utilities & greetings ($0.00, < 1ms).
  - `SMALL_MODEL`: Lightweight models (Llama 3.1 8B, GPT-4o-mini) at $0.15 / $0.60 per 1M tokens.
  - `FRONTIER_MODEL`: Flagship reasoning models (Claude 3.5 Sonnet, GPT-4o) at $2.50 / $10.00+ per 1M tokens.
  - `HUMAN_REVIEW`: Quarantined security sandbox.

### 🛡️ 5. Enterprise Reliability Engineering
- **Three-State Circuit Breakers:** Protects both decision and provider tiers with `CLOSED`, `OPEN`, and `HALF_OPEN` state transitions.
- **Exponential Backoff with Full Jitter:** Prevents thundering herd problems during downstream model provider outages.
- **Automatic Multi-Tier Failover:** Seamlessly re-routes queries from failing providers down to resilient backup models.

### 📊 6. Full Observability & Waterfall Flamegraphs
- **Sub-Millisecond Waterfall Spans:** Measures exact duration of `Jev Decision`, `Policy Checks`, `Provider Generation`, and `Gateway Overhead`.
- **Statistical Analytics:** Calculates P50, P95, and P99 latencies using linear interpolation.
- **Counter-Factual Cost Accounting:** Real-time formula calculating exact dollars saved vs. a 100% Frontier baseline.
- **Strict Privacy Invariant:** Prompts and sensitive user content are **never stored** in the database—only categorical and performance metadata.

### 💻 7. Next.js Observability Dashboard
- **Interactive Routing Playground:** Live prompt tester with preset archetypes, constraint sliders, and animated flamegraphs.
- **Trace Explorer:** Filterable distributed spans with expandable waterfall and token economics inspection.
- **A/B Benchmark Matrix:** Live trigger to execute 3-way comparative evaluations across Baseline, Rules, and JevFlow.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    Client(["User / Client App"]) -->|POST /v1/chat| Gateway["JevFlow Perimeter"]
    
    subgraph Perimeter["Perimeter & Gatekeeping"]
        Gateway --> RateLimiter{"Token Bucket\nRate Limiter"}
        RateLimiter -->|Quota Exceeded| HTTP429["429 Too Many Requests\n(Retry-After Header)"]
        RateLimiter -->|Allowed| CacheLookup{"Canonical SHA-256\nCache Check (Redis)"}
    end

    CacheLookup -->|CACHE HIT (0ms, $0.00)| CachedResponse(["Instant Response"])
    
    subgraph DecisionLayer["Cognitive Decision Layer"]
        CacheLookup -->|CACHE MISS| JevClient["TypeSafe Jev Client\n(System One API)"]
        JevClient -.->|Timeout / Outage| MockEngine["Calibrated Offline\nFallback Engine"]
        JevClient --> JevOutput["Decision Tuple:\n• Intent (Choice)\n• Complexity (0.0-2.0)\n• Safety Probability\n• Route Recommendation"]
        MockEngine --> JevOutput
    end

    subgraph PolicyEngine["Deterministic Policy Engine (8 Gates)"]
        JevOutput --> G1{"Gate 1: Safety Check"}
        G1 -->|Unsafe| HR["Human Review Route"]
        G1 -->|Safe| G2{"Gate 2: Provider Outage?"}
        G2 -->|Yes| Failover["Failover to Backup"]
        G2 -->|No| G3{"Gate 3: High Concurrency (>80%)?"}
        G3 -->|Yes| Shed["Shed Load to Small Model"]
        G3 -->|No| G4{"Gate 4: Latency Budget Exceeded?"}
        G4 -->|Yes| ClampSmall["Clamp to Small Model"]
        G4 -->|No| G5{"Gate 5: Token-Aware Cost Exceeded?"}
        G5 -->|Yes| ClampCost["Clamp Route"]
        G5 -->|No| G6{"Gate 6: Low Confidence (<0.60)?"}
        G6 -->|Yes| Escalate["Escalate to Frontier"]
        G6 -->|No| G7["Complexity / Intent Mapping"]
    end

    subgraph Providers["Execution Providers (Circuit Breaker Protected)"]
        G7 --> Deterministic["Deterministic Provider\n($0.00, < 1ms)"]
        G7 --> SmallModel["Small Model (Llama 3.1 8B / GPT-4o-mini)\n($0.15 - $0.60 / 1M)"]
        G7 --> FrontierModel["Frontier Model (Claude 3.5 Sonnet / GPT-4o)\n($2.50 - $10.00 / 1M)"]
        HR --> ReviewProvider["Human Review Sandbox"]
    end

    subgraph Observability["Telemetry & Accounting"]
        Deterministic --> Telemetry["Telemetry Repository"]
        SmallModel --> Telemetry
        FrontierModel --> Telemetry
        ReviewProvider --> Telemetry
        Telemetry --> DB[(Async SQLite / Postgres)]
        Telemetry --> Dashboard["Next.js Real-time Dashboard"]
    end

    Providers --> FinalResponse(["Unified Gateway Response"])
```

---

## 📈 Empirical Benchmark Evaluation

We evaluated JevFlow across a curated benchmark dataset of **12 diverse prompt archetypes** (Trivial Greetings, Factual Lookups, Simple Boilerplate Code, Complex Low-Level Systems Concurrency, Multi-Causal Historical Synthesis, Mathematical Proofs, Ambiguous Queries, and Adversarial Injections) against two standard industry patterns:

| Evaluation Metric | Baseline (100% Frontier) | Strategy A (Static Rules) | Strategy B (JevFlow Adaptive) |
|---|:---:|:---:|:---:|
| **Requests Evaluated** | 12 | 12 | **12** |
| **Route Match / Optimal Alignment** | 33.3% | 50.0% | **83.3%** 🏆 |
| **Median Latency (P50)** | 141.79 ms | 47.11 ms | **64.06 ms** (-54.8%) |
| **Tail Latency (P95)** | 154.94 ms | 147.62 ms | **165.40 ms** |
| **Tail Latency (P99)** | 155.17 ms | 154.41 ms | **168.76 ms** |
| **Total Token Cost ($)** | $0.011241 | $0.002930 | **$0.002665** |
| **Net Cost Reduction vs. Baseline** | 0.0% | 65.5% | **66.3% Saved** 💰 |
| **Cache Hit Rate (Repeated Traffic)** | 0.0% | 0.0% | **8.3%** |
| **Circuit Breaker / Outage Failover** | 0.0% | 0.0% | **100% Resilient** |

---

## 💻 Tech Stack & Design Rationale

| Category | Technology | Why We Chose It |
|---|---|---|
| **Backend Core** | Python 3.12 + FastAPI | Native asynchronous event loop, automatic OpenAPI documentation, high-throughput ASGI performance. |
| **Data Validation** | Pydantic V2 | Rust-accelerated schema validation, strict runtime type safety, clean environment variable ingestion. |
| **Frontend UI** | Next.js 16 (React 19, TypeScript) | Server-side rendering, App Router modularity, fast client-side state hydration, production readiness. |
| **Styling** | Vanilla CSS (Glassmorphism Dark Theme) | Zero CSS-in-JS runtime overhead, full control over micro-animations, customizable responsive design system. |
| **Distributed Cache** | Redis 7 + Local Memory Fallback | Sub-millisecond atomic key lookups, TTL expiration, zero-downtime in-memory fallback. |
| **Database & ORM** | SQLAlchemy 2.0 (Async) + aiosqlite / PostgreSQL | Non-blocking database I/O, strict relational indexing, seamless local SQLite $\rightarrow$ production Postgres transition. |
| **AI Decision Layer** | TypeSafe Jev OpenAPI 3.1 Client | Simultaneous multi-question probabilistic classification with continuous rubric scoring. |
| **Model Inference** | OpenRouter / OpenAI / Groq / Ollama | Universal vendor-agnostic chat completions client with token tracking and cost calculation. |
| **Testing** | Pytest + pytest-asyncio + httpx MockTransport | 49 isolated unit and integration tests executing in < 4 seconds with zero network flakiness. |
| **DevOps** | Docker & Docker Compose | Multi-container reproducible orchestration for Redis, FastAPI backend, and Next.js frontend. |

---

## 🛠️ Installation & Setup Guide

### Option A: 1-Click Docker Compose (Recommended)

Make sure **Docker Desktop** is running, then run:

```bash
# 1. Clone the repository
git clone https://github.com/tusharkkp/JevFlow.git
cd JevFlow

# 2. Configure your environment
cp .env.example .env
# Edit .env and paste your OpenRouter / OpenAI API key

# 3. Launch Redis, Backend, and Frontend containers
docker compose up -d

# 4. View container status
docker compose ps
```

- **Next.js Observability Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Core & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Gateway Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Local Manual Setup (Development Mode)

#### 1. Backend Setup (FastAPI)
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run test suite to verify 49 passing tests
pytest -v backend/tests/

# Start FastAPI Gateway
uvicorn backend.app.main:app --port 8000 --reload
```

#### 2. Frontend Setup (Next.js)
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## ⚙️ Environment Variables (`.env`)

| Variable | Default Value | Required | Description |
|---|:---:|:---:|---|
| `ENVIRONMENT` | `development` | No | Application runtime environment (`development` / `production`). |
| `PORT` | `8000` | No | FastAPI server port. |
| `HOST` | `0.0.0.0` | No | Network binding host address. |
| `OPENAI_API_KEY` | *Empty* | **Yes (for live models)** | Your **OpenRouter** or **OpenAI** API key (e.g. `sk-or-v1-...`). If empty, offline calibrated providers are used. |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` | No | Base URL for LLM chat completions (OpenRouter, Groq, Ollama, OpenAI). |
| `SMALL_MODEL_NAME` | `meta-llama/llama-3.1-8b-instruct:free` | No | Model identifier for the Small Model tier. |
| `FRONTIER_MODEL_NAME` | `anthropic/claude-3.5-sonnet` | No | Model identifier for the Frontier Model tier. |
| `TYPESAFE_API_KEY` | *Empty* | Optional | Your TypeSafe Jev API key for live System One decisions. If empty, offline engine is used. |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` | No | Endpoint URL for the TypeSafe Jev service. |
| `REDIS_URL` | `redis://localhost:6379/0` | Optional | Connection URI for Redis cache. Overridden in Docker Compose to `redis://redis:6379/0`. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./jevflow_telemetry.db` | No | Async SQLAlchemy database URI (SQLite for local, Postgres for production). |
| `MAX_LATENCY_BUDGET_MS` | `2000` | No | Gateway ceiling latency budget in milliseconds. |
| `MAX_COST_PER_REQUEST` | `0.05` | No | Maximum token expenditure per request in USD ($). |

---

## 📡 API Reference Documentation

### 1. Process Chat Prompt
```http
POST /v1/chat
Content-Type: application/json
```
**Request Body:**
```json
{
  "prompt": "Design a high-throughput lock-free ring buffer in C++.",
  "latency_budget_ms": 1500,
  "cost_budget": 0.05,
  "user_id": "client_enterprise_01"
}
```

**Response (200 OK):**
```json
{
  "request_id": "req_8f17a992bc",
  "content": "[Claude 3.5 Sonnet / Frontier Model] Detailed architectural design...",
  "route": "frontier_model",
  "model": "anthropic/claude-3.5-sonnet",
  "telemetry": {
    "intent": "coding",
    "complexity_score": 1.85,
    "jev_confidence": 0.94,
    "selected_route": "frontier_model",
    "policy_reason": "High complexity (1.85 >= 1.20) warrants frontier model.",
    "actual_model": "anthropic/claude-3.5-sonnet",
    "cache_hit": false,
    "jev_latency_ms": 11.4,
    "model_latency_ms": 138.2,
    "gateway_overhead_ms": 1.8,
    "total_latency_ms": 151.4,
    "input_tokens": 14,
    "output_tokens": 85,
    "estimated_cost_usd": 0.000885,
    "baseline_cost_usd": 0.000885,
    "cost_saved_usd": 0.000000
  }
}
```

### 2. Fleet Telemetry Aggregations
```http
GET /v1/telemetry/summary
```
**Response (200 OK):**
```json
{
  "total_requests": 142,
  "p50_latency_ms": 64.06,
  "p95_latency_ms": 165.40,
  "p99_latency_ms": 168.76,
  "average_latency_ms": 78.42,
  "total_cost_usd": 0.038410,
  "total_cost_saved_usd": 0.075420,
  "cost_reduction_percent": 66.3,
  "cache_hit_rate_percent": 8.3,
  "fallback_rate_percent": 0.0,
  "circuit_breaker_trip_count": 0,
  "route_distribution": {
    "deterministic": { "count": 24, "percentage": 16.9 },
    "small_model": { "count": 68, "percentage": 47.9 },
    "frontier_model": { "count": 38, "percentage": 26.8 },
    "human_review": { "count": 12, "percentage": 8.4 }
  }
}
```

### 3. Run Comparative Benchmark
```http
POST /v1/experiments/run?strategy=all
```
Executes the 12-archetype comparative suite and returns side-by-side matrices comparing **Baseline**, **Static Rules**, and **JevFlow Adaptive**.

---

## 📂 Project Directory Tree

```
JevFlow/
├── backend/
│   ├── app/
│   │   ├── cache/              # Canonical SHA-256 Memory & Redis Cache
│   │   │   ├── base.py
│   │   │   ├── memory_cache.py
│   │   │   └── redis_cache.py
│   │   ├── core/               # Centralized Pydantic BaseSettings config
│   │   │   └── config.py
│   │   ├── db/                 # Async SQLAlchemy database models & session
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── decision/           # System One Decision Layer
│   │   │   ├── base.py
│   │   │   ├── jev_engine.py   # TypeSafe Jev API integration
│   │   │   └── mock_engine.py  # Calibrated offline fallback engine
│   │   ├── experiments/        # Evaluation Engine & Benchmarking
│   │   │   ├── dataset.py      # 12-archetype curated ground-truth dataset
│   │   │   ├── runner.py       # Benchmark orchestrator & table generator
│   │   │   └── strategies.py   # Baseline vs Rules vs JevFlow strategies
│   │   ├── jev/                # Resilient HTTP Client for TypeSafe API
│   │   │   ├── client.py
│   │   │   └── exceptions.py
│   │   ├── policy/             # Deterministic 8-Gate Business Logic Engine
│   │   │   ├── policy_engine.py
│   │   │   └── state.py        # Real-time concurrency & provider health tracker
│   │   ├── providers/          # Universal Model Provider Abstraction
│   │   │   ├── base.py
│   │   │   ├── deterministic_provider.py
│   │   │   ├── small_model_provider.py
│   │   │   ├── frontier_model_provider.py
│   │   │   ├── openai_provider.py      # OpenRouter / OpenAI HTTP provider
│   │   │   ├── human_review_provider.py
│   │   │   └── registry.py             # Automatic failover router
│   │   ├── rate_limiter/       # Token Bucket Algorithm implementation
│   │   │   └── token_bucket.py
│   │   ├── reliability/        # Fault-tolerance primitives
│   │   │   ├── circuit_breaker.py      # 3-State async circuit breaker
│   │   │   └── retry.py                # Exponential backoff with jitter
│   │   ├── schemas/            # Pydantic V2 Request, Decision & Response models
│   │   ├── services/           # GatewayService end-to-end pipeline orchestrator
│   │   ├── telemetry/          # P50/P95/P99 math & async persistence repository
│   │   └── main.py             # FastAPI ASGI server entrypoint
│   ├── tests/                  # 49 unit and integration tests
│   ├── Dockerfile              # Python 3.12 slim backend containerfile
│   └── requirements.txt        # Frozen dependencies
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css     # Obsidian dark theme & design system tokens
│   │   │   ├── layout.tsx      # SEO metadata & viewport configuration
│   │   │   └── page.tsx        # Observability Dashboard page orchestrator
│   │   ├── components/         # Modular UI components
│   │   │   ├── Header.tsx      # System health bar & perimeter indicators
│   │   │   ├── KpiGrid.tsx     # Fleet accounting cards & route allocation bar
│   │   │   ├── Playground.tsx  # Interactive prompt tester & waterfall flamegraph
│   │   │   ├── TraceTable.tsx  # Filterable distributed span table with inspector
│   │   │   └── BenchmarkView.tsx # 3-way evaluation matrix runner
│   │   └── lib/                # Typed API client & frontend interfaces
│   ├── Dockerfile              # Multi-stage production containerfile
│   └── package.json            # Next.js 16 + React 19 dependencies
├── docs/                       # Comprehensive Engineering Documentation
│   ├── ARCHITECTURE.md         # Full system architecture specification
│   ├── DECISION_WORKFLOW.md    # Multi-question System One prompt formulations
│   ├── ROUTING.md              # Provider abstractions & cost calculations
│   ├── POLICY_ENGINE.md        # 8-gate policy rules & threshold tables
│   ├── EVALUATION.md           # Empirical benchmark analysis & insights
│   ├── EXPERIMENTS.md          # Benchmark execution CLI & API manual
│   ├── DASHBOARD.md            # Frontend architecture & component hierarchy
│   ├── DOCKER.md               # Containerization & Docker Compose manual
│   └── LEARNING_NOTES.md       # Complete 10-phase engineering journal
├── .dockerignore
├── .env.example                # Configuration template
├── .gitignore
├── docker-compose.yml          # Orchestration for Redis, Backend, and Frontend
├── LICENSE                     # MIT Open Source License
└── README.md                   # Project documentation
```

---

## ⚡ Performance, Scalability & Security Invariants

1. **Sub-Millisecond Cache Invariant:** Repeated queries bypass both the decision engine and provider execution entirely, returning in `< 1ms` with `$0.00` token cost and `cache_hit: true`.
2. **P95 Latency Safety Margin:** To protect client SLAs against network jitter, the policy engine scales observed P50 latency by $2.2\times$ when evaluating against user latency budgets.
3. **Database Privacy by Design:** The `requests` database schema strictly excludes prompt text and LLM generation strings. Only categorical metadata, latency numbers, and token counts are persisted.
4. **Perimeter Defense:** Token-bucket rate limiting rejects denial-of-service traffic at the perimeter before downstream model tokens or third-party API quotas are consumed.

---

## 🗺️ Roadmap & Future Scope

- [ ] **Semantic Vector Caching:** Replace exact string hashing with Qdrant / PgVector embedding similarity search for fuzzy cache hits.
- [ ] **Multi-Region Failover:** Dynamic geo-routing across AWS / GCP regions for multi-cluster gateway deployments.
- [ ] **Streaming Token Waterfalls:** Server-Sent Events (SSE) streaming support with Time-to-First-Token (TTFT) observability.
- [ ] **Automated Rubric Weight Calibration:** Continuous reinforcement learning loop adjusting complexity thresholds based on downstream user feedback.

---

## 🤝 Contributing

Contributions to JevFlow are welcome! Follow these steps to contribute:

1. **Fork the Repository** on GitHub.
2. **Create a Feature Branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Write Tests:** Ensure all new features have test coverage in `backend/tests/`.
4. **Verify Test Suite:**
   ```bash
   pytest -v backend/tests/
   ```
5. **Commit Your Changes:**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
6. **Push to Your Branch:**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request** with a detailed explanation of your changes.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](file:///c:/PROJECTS/New%20folder/LICENSE) for more information.

---

## 👤 Author & Credits

**Tushar Kaldate**  
- **GitHub:** [@tusharkkp](https://github.com/tusharkkp)  
- **LinkedIn:** [https://www.linkedin.com/in/tushar-kaldate-2b5276262/](https://www.linkedin.com/in/tushar-kaldate-2b5276262/)  
- **Project Repository:** [https://github.com/tusharkkp/JevFlow](https://github.com/tusharkkp/JevFlow)

*Built with passion to advance the engineering principles of System One Decisions and Adaptive AI Architectures.*
