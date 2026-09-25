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
