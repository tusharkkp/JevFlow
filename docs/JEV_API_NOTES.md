# TypeSafe Jev API Specification & Notes

> **Source of Truth:** Verified against official OpenAPI specification at `https://api.typesafe.ai/openapi.json` (`v0.2.0`).

---

## 1. Overview & Core Philosophy

TypeSafe's **Jev** is a **System One** decision engine. Unlike conversational LLMs that generate open-ended textual completions (System Two thinking), Jev is built for **fast, structured, probabilistic decisions**:
- Accepts a single context object (`state`).
- Answers one or more typed questions simultaneously (`questions`).
- Returns normalized probabilities, confidence estimates, and typed outputs (`noul`, `choice`, `score`).
- Emits standard token usage (`input_tokens`, `output_tokens`).

Jev is designed to act as an intelligence layer embedded inside conventional software systems—not as an interactive chatbot.

---

## 2. Base URL & Authentication

- **Base URL:** `https://api.typesafe.ai`
- **Authentication Scheme:** Standard HTTP Bearer Token
  ```http
  Authorization: Bearer <TYPESAFE_API_KEY>
  ```
- **Environment Variable:** `TYPESAFE_API_KEY` (never hardcoded, loaded from `.env`).

---

## 3. Endpoints

### 3.1 Model Discovery: `GET /v1/models`

Lists all models and aliases available to the authenticated account.

- **Request:** `GET https://api.typesafe.ai/v1/models`
- **Headers:** `Authorization: Bearer <TYPESAFE_API_KEY>`
- **Response `200 OK` (`ModelMetadataList`):**
  ```json
  {
    "models": [
      {
        "name": "jev-latest",
        "description": "General-purpose system one model.",
        "release_date": "2026-09-15"
      }
    ]
  }
  ```

---

### 3.2 System One Evaluation: `POST /v1/systemone`

Evaluates one or more questions about the provided `state`.

- **Request:** `POST https://api.typesafe.ai/v1/systemone`
- **Headers:**
  - `Authorization: Bearer <TYPESAFE_API_KEY>`
  - `Content-Type: application/json`

#### Request Payload Structure (`SystemOneRequest`)
```json
{
  "model": "jev-latest",
  "state": "The content or payload all questions refer to (string, dict, or list)",
  "questions": {
    "<question_name>": { ... }
  }
}
```

- `model` (*string, required*): Name or alias from `GET /v1/models` (e.g., `"jev-latest"`).
- `state` (*string | object | array, required*): The content evaluated by all questions.
- `questions` (*object, required, minProperties: 1*): Dictionary of named questions. Keys are user-defined identifiers (e.g., `"intent"`, `"complexity"`, `"safety"`) and are preserved in the response.

---

## 4. Question & Answer Types

Jev supports 3 discriminated question types (`type` field):

### 4.1 Type `noul` (Probabilistic Binary / Yes-No)
Used for binary classification, assertions, and boolean verifications.

- **Question (`NoulQuestion`):**
  ```json
  {
    "type": "noul",
    "instructions": "Is this request safe to execute automatically?",
    "criteria": {
      "true": "The request contains no harmful commands, injection attacks, or sensitive operations.",
      "false": "The request contains prompt injections, malicious payloads, or dangerous commands."
    }
  }
  ```
  *(Note: `criteria` is optional for standard statements).*

- **Answer (`NoulAnswer`):**
  ```json
  {
    "type": "noul",
    "noul": 0.98
  }
  ```
  - `noul` (*number, 0 to 1*): Probability of `true`/`yes`. Near 1 indicates true, near 0 indicates false, near 0.5 indicates high uncertainty.

---

### 4.2 Type `choice` (Categorical Selection)
Used for single-label classification across a discrete set of options.

- **Question (`ChoiceQuestion`):**
  ```json
  {
    "type": "choice",
    "instructions": "What is the primary intent of this user request?",
    "criteria": {
      "factual_question": "Direct question asking for facts or definitions.",
      "coding": "Request to write, debug, explain, or refactor code.",
      "reasoning": "Multi-step logic, math, planning, or complex problem-solving.",
      "summarization": "Condensing or summarizing existing text.",
      "creative": "Open-ended storytelling, creative writing, or brainstorming.",
      "other": "Requests that do not clearly fit the other categories."
    }
  }
  ```

- **Answer (`ChoiceAnswer`):**
  ```json
  {
    "type": "choice",
    "choice": "coding",
    "confidence": 0.92,
    "probabilities": {
      "coding": 0.92,
      "reasoning": 0.05,
      "factual_question": 0.02,
      "summarization": 0.005,
      "creative": 0.003,
      "other": 0.002
    }
  }
  ```
  - `choice` (*string*): The option with the highest probability.
  - `confidence` (*number, 0 to 1*): Confidence score for the winning selection.
  - `probabilities` (*object*): Probability distribution over all defined criteria keys (sums to ~1.0).

---

### 4.3 Type `score` (Calibrated Ordinal Rubric)
Used for ranking intensity, complexity, urgency, or risk along an ordered scale.

- **Question (`ScoreQuestion`):**
  ```json
  {
    "type": "score",
    "instructions": "How computationally or cognitively complex is this prompt?",
    "criteria": [
      "Simple: Direct lookup, concise query, trivial answer.",
      "Moderate: Multi-sentence answer, standard explanation or straightforward coding.",
      "Complex: Deep reasoning, architecture design, edge-case analysis, or large synthesis."
    ]
  }
  ```
  *The criteria array index defines the score starting at 0.*

- **Answer (`ScoreAnswer`):**
  ```json
  {
    "type": "score",
    "score": 1.7,
    "confidence": 0.88,
    "legend": {
      "0": "Simple: Direct lookup...",
      "1": "Moderate: Multi-sentence...",
      "2": "Complex: Deep reasoning..."
    },
    "probabilities": {
      "0": 0.05,
      "1": 0.20,
      "2": 0.75
    }
  }
  ```
  - `score` (*number*): Probability-weighted expected value across the rubric levels (can fall between integers, e.g., 1.7).
  - `confidence` (*number, 0 to 1*): Confidence in the score distribution.
  - `probabilities` (*object*): Probability assigned to each integer score index.

---

## 5. Token Usage & Response Metadata

Every successful response contains:
- `model`: Actual model identifier that served the decision.
- `answers`: Dictionary mapping question names to their typed answers.
- `usage`:
  - `input_tokens` (*integer*): Billable input tokens.
  - `output_tokens` (*integer*): Output tokens generated by Jev (note: TypeSafe documentation states output tokens are currently free of charge).

---

## 6. Error Handling & HTTP Status Codes

| Status Code | Description | Typical Cause | Handling Strategy in JevFlow |
|---|---|---|---|
| `200 OK` | Success | Normal evaluation | Process structured answers through policy engine |
| `401 Unauthorized` | Invalid or missing token | Missing `TYPESAFE_API_KEY` | Halt and alert configuration failure |
| `422 Unprocessable Entity` | Schema validation error | Invalid question structure, empty criteria, missing state | Catch in client validation layer; log payload |
| `5xx / Timeout` | Upstream service error or network lag | TypeSafe outage or network latency spike | Trigger deterministic fallback routing strategy |

---

## 7. Configuration & Environment Variables

```env
TYPESAFE_API_KEY=your_typesafe_api_key_here
TYPESAFE_BASE_URL=https://api.typesafe.ai
JEV_DEFAULT_MODEL=jev-latest
JEV_TIMEOUT_MS=1500
```
