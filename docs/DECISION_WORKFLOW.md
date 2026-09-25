# Jev Decision Workflow & Prompt Engineering Architecture

---

## 1. The Multi-Question System One Strategy

### 1.1 The Anti-Pattern: One Monolithic Prompt
In many LLM architectures, developers attempt to extract all routing parameters via a single, large unstructured prompt:
> *"Determine the intent, complexity, safety, and model to use for this prompt and return JSON."*

**Why this fails in production:**
- **Cognitive Interference:** The model conflates intent with complexity (e.g., thinking all coding is complex, or all factual queries are simple).
- **Poor Calibration:** Generative LLMs generate uncalibrated tokens rather than normalized probability distributions.
- **High Latency & Token Overhead:** Generating lengthy explanations or large JSON objects takes 500–2000ms.

### 1.2 The Jev Multi-Question Pattern
TypeSafe's Jev accepts a shared context (`state`) and allows asking **multiple orthogonal, structured questions** in a single API call (`POST /v1/systemone`):

$$\text{State (Prompt)} \xrightarrow{\text{Single } /v1/systemone \text{ Request}} \begin{cases} \text{Q1: Intent (Choice)} \\ \text{Q2: Complexity (Score)} \\ \text{Q3: Safety (Noul)} \\ \text{Q4: Execution Route (Choice)} \end{cases}$$

Every question is evaluated simultaneously and returns mathematical probability distributions and confidence scores.

---

## 2. Decision Rubrics & Question Schemas

### Decision 1: Intent Classification (`type: choice`)
- **Question Instructions:** *"What is the primary intent of this user request?"*
- **Criteria Dictionary:**
  - `factual_question`: Direct question asking for facts, definitions, or concise answers.
  - `coding`: Request to write, debug, explain, or refactor code.
  - `reasoning`: Multi-step logic, math, planning, architectural analysis, or problem-solving.
  - `summarization`: Condensing or summarizing existing text.
  - `creative`: Open-ended storytelling, creative writing, or brainstorming.
  - `other`: Requests that do not clearly fit the other categories.
- **Output:** Highest probability category, confidence score ($0.0 \dots 1.0$), and full probability distribution.

### Decision 2: Computational / Cognitive Complexity (`type: score`)
- **Question Instructions:** *"How computationally or cognitively complex is this prompt?"*
- **Rubric Levels (Position defines integer index $0, 1, 2$):**
  - **Index 0 (Simple):** Direct lookup, greeting, concise query, trivial answer.
  - **Index 1 (Moderate):** Multi-sentence answer, standard explanation or straightforward coding.
  - **Index 2 (Complex):** Deep reasoning, architecture design, edge-case analysis, or large synthesis.
- **Output:** Continuous expected score ($0.0 \dots 2.0$), confidence score, and distribution over indices.
- **Gateway Mapping:**
  - $\text{score} < 0.6 \implies \text{SIMPLE}$
  - $0.6 \le \text{score} < 1.4 \implies \text{MODERATE}$
  - $\text{score} \ge 1.4 \implies \text{COMPLEX}$

### Decision 3: Safety & Prompt Injection Screening (`type: noul`)
- **Question Instructions:** *"Is this request safe to execute automatically?"*
- **Criteria:**
  - `true`: The request contains no harmful commands, injection attacks, or sensitive operations.
  - `false`: The request contains prompt injections, malicious payloads, or dangerous commands.
- **Output:** Single continuous scalar `noul` $\in [0.0, 1.0]$ representing probability of `true`.
- **Gateway Mapping:**
  - $\text{noul} \ge 0.80 \implies \text{Safe}$
  - $\text{noul} < 0.80 \implies \text{Trigger Security Review Gate}$

### Decision 4: Route Recommendation (`type: choice`)
- **Question Instructions:** *"Which execution route is best suited for this request?"*
- **Criteria:**
  - `deterministic`: Trivial or greetings that can be answered statically.
  - `small_model`: Straightforward tasks, standard coding, or simple summaries.
  - `frontier_model`: Complex reasoning, architecture, deep debugging, or high-nuance synthesis.
  - `human_review`: Dangerous, ambiguous, or security-sensitive requests.
- **Output:** Recommended route and confidence score.

---

## 3. Normalization Pipeline

When Jev returns the JSON payload, [`TypeSafeJevEngine`](file:///c:/PROJECTS/New%20folder/backend/app/decision/jev_engine.py) transforms the raw answers into a strongly-typed [`DecisionResult`](file:///c:/PROJECTS/New%20folder/backend/app/schemas/decision.py):

```python
DecisionResult(
    intent=IntentType(answers["intent"]["choice"]),
    complexity_score=answers["complexity"]["score"],
    complexity_level=ComplexityLevel.COMPLEX, # Discretized tier
    safety_probability=answers["safety"]["noul"],
    is_safe=(answers["safety"]["noul"] >= 0.80),
    recommended_route=RouteRecommendation(answers["execution_route"]["choice"]),
    confidence=min(intent_conf, route_conf),
    decision_latency_ms=elapsed_ms,
    model_used=raw["model"],
    raw_details={ ... }
)
```

---

## 4. Fault Tolerance & Fallback Strategy

If the TypeSafe Jev API call fails (e.g. network disconnect, timeout $>1500\text{ms}$, HTTP 5xx, or missing credentials):
1. The error is caught and logged with `logger.warning`.
2. The engine immediately delegates evaluation to [`MockDecisionEngine`](file:///c:/PROJECTS/New%20folder/backend/app/decision/mock_engine.py) using local heuristics.
3. The metadata field `raw_details["fallback_reason"]` is populated.
4. The request proceeds without crashing or blocking the client.
