# Model Routing & Provider Abstraction Architecture

---

## 1. Provider Abstraction Philosophy

In production AI architectures, tight coupling to a single model provider (e.g., hardcoding OpenAI or Anthropic SDK calls directly inside business endpoints) creates critical vulnerabilities:
- **Vendor Lock-in:** Switching models requires refactoring application endpoints.
- **Outage Vulnerability:** When a vendor suffers an API outage or rate-limit spike, the entire application goes down.
- **Uncontrolled Cost Escalation:** Without dynamic routing, simple requests consume the same expensive token quotas as deep reasoning tasks.

### The Strategy Pattern in JevFlow
JevFlow decouples the gateway from any specific LLM using the **Strategy Pattern**:

```
                              ModelProvider (Interface)
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
            ▼                          ▼                          ▼
   DeterministicProvider       SmallModelProvider        FrontierModelProvider
   - Model: rule-v1            - Model: small-fast-v1    - Model: frontier-v1
   - Cost: $0.00               - In: $0.25 / 1M          - In: $3.00 / 1M
   - Latency: ~1ms             - Out: $1.25 / 1M         - Out: $15.00 / 1M
                               - Latency: ~35ms          - Latency: ~140ms
```

Every provider implements the unified interface:
- `generate(prompt: str, **kwargs) -> ProviderResponse`
- `estimate_cost(input_tokens: int, output_tokens: int) -> float`
- `health() -> ProviderHealth`
- `metadata -> Dict[str, Any]`

---

## 2. Provider Tiers & Cost Modeling

| Tier | Representative Models | Input Cost / 1M | Output Cost / 1M | Target Use Case | Typical Latency |
|---|---|---|---|---|---|
| **Deterministic** | Regex / Keyword / Knowledge Lookup | **$0.00** | **$0.00** | Greetings, health pings, static queries | $\sim 1\text{ms}$ |
| **Small Model** | Claude 3.5 Haiku, GPT-4o-mini, Llama 3.2 3B | **$0.25** | **$1.25** | Summaries, factual answers, light code | $\sim 35\text{ms}$ |
| **Frontier Model** | Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro | **$3.00** | **$15.00** | Multi-step reasoning, architecture, deep math | $\sim 150\text{ms}$ |
| **Human Review** | Quarantine / Audit Queue | **$0.00** | **$0.00** | Security risks, prompt injection, policy flags | $\sim 1\text{ms}$ |

### Cost Calculation Formula
For any model execution:
$$\text{Cost}_{\text{actual}} = \left(\frac{T_{\text{in}}}{10^6} \times P_{\text{in}}\right) + \left(\frac{T_{\text{out}}}{10^6} \times P_{\text{out}}\right)$$

### Cost Savings Accounting
The gateway constantly calculates the counter-factual baseline cost:
$$\text{Cost}_{\text{baseline}} = \text{Cost if routed to Frontier Model}$$
$$\text{Cost Saved} = \max\left(0, \text{Cost}_{\text{baseline}} - \text{Cost}_{\text{actual}}\right)$$

---

## 3. Provider Registry & Failover Engine

The [`ProviderRegistry`](file:///c:/PROJECTS/New%20folder/backend/app/providers/registry.py) maps the deterministic policy output (`RouteType`) to the target execution engine:

```python
RouteType.DETERMINISTIC   ──► DeterministicProvider
RouteType.SMALL_MODEL     ──► SmallModelProvider
RouteType.FRONTIER_MODEL  ──► FrontierModelProvider
RouteType.HUMAN_REVIEW    ──► HumanReviewProvider
RouteType.FALLBACK        ──► SmallModelProvider
```

### Failover Mechanics
If the primary provider throws an exception (e.g. rate limit, connection drop, or unexpected failure):
1. The error is logged: `Primary provider failed for route 'frontier_model': ...`
2. The registry engages the fallback provider:
   - If `frontier_model` fails $\longrightarrow$ failover to `small_model`.
   - If `small_model` fails $\longrightarrow$ failover to `deterministic_provider`.
3. The response is stamped with `fallback_triggered: true` and `fallback_reason: "provider_failure: <error>"`.
4. The user request succeeds seamlessly rather than throwing a 500 error.
