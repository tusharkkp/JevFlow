# JevFlow — Adaptive AI Gateway
### Powered by System One Decisions

> JevFlow is an educational, production-style AI gateway designed to demonstrate how fast, structured probabilistic decisions (System One models like TypeSafe Jev) combined with deterministic policy enforcement enable intelligent, cost-effective, and low-latency model routing.

---

## 🚀 Core Philosophy

Traditional AI applications blindly send every request directly to expensive, slow frontier models (System Two). JevFlow introduces a decision-policy pipeline:

$$\text{Client} \longrightarrow \text{API Gateway} \longrightarrow \text{System One Decisions} \longrightarrow \text{Deterministic Policy} \longrightarrow \text{Adaptive Route} \longrightarrow \text{Telemetry}$$

1. **Jev = Probabilistic Intelligence:** Evaluates intent, estimates complexity, assesses safety, and assigns confidence.
2. **Policy Engine = Deterministic Enforcement:** Enforces security gates, latency/cost budgets, and fallback rules.
3. **Model Providers = Vendor-Agnostic Execution:** Small models, frontier models, cache, or deterministic logic.
4. **Telemetry = Evidence:** Tracks P50/P95/P99 latency, token usage, and real dollar cost savings vs. baseline.

---

## 📁 Repository Structure

```
jevflow/
├── backend/
│   ├── app/
│   │   ├── core/           # Centralized Pydantic settings & config
│   │   ├── schemas/        # Request, Decision, and Response Pydantic models
│   │   ├── decision/       # System One DecisionEngine interface & mock implementation
│   │   ├── policy/         # Deterministic PolicyEngine with configurable gates
│   │   ├── providers/      # Vendor-agnostic ModelProvider abstraction & mock engine
│   │   ├── services/       # GatewayService orchestrator
│   │   └── main.py         # FastAPI application entrypoint
│   ├── tests/              # Pytest unit and integration test suite
│   ├── pyproject.toml      # Project metadata and dependencies
│   └── requirements.txt    # Frozen pip dependencies
├── docs/
│   ├── ARCHITECTURE.md     # Comprehensive system architecture & pipeline specification
│   ├── JEV_API_NOTES.md    # Verified TypeSafe Jev API contract from official OpenAPI spec
│   └── LEARNING_NOTES.md   # Architectural journal & concepts explained per milestone
├── .env.example            # Environment configuration template
├── .gitignore              # Git ignore rules
└── pytest.ini              # Pytest configuration
```

---

## 🛠️ Quick Start (Phase 1)

### 1. Set Up Environment & Install Dependencies
```bash
# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Run Test Suite
```bash
pytest -v
```

### 3. Run Gateway Server Locally
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Visit the interactive OpenAPI documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

### 4. Send a Sample Request
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/v1/chat" -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"prompt": "Hello!"}' | ConvertTo-Json -Depth 5
```
