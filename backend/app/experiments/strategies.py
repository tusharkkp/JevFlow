import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any

from backend.app.schemas.request import GatewayRequest
from backend.app.schemas.response import GatewayResponse, TelemetryTrace, RouteType
from backend.app.services.gateway_service import GatewayService
from backend.app.providers.registry import ProviderRegistry
from backend.app.providers.frontier_model_provider import FrontierModelProvider
from backend.app.providers.small_model_provider import SmallModelProvider
from backend.app.providers.deterministic_provider import DeterministicProvider


class RoutingStrategy(ABC):
    """Abstract interface for comparative routing strategies."""
    name: str

    @abstractmethod
    async def process(self, request: GatewayRequest) -> GatewayResponse:
        pass


class BaselineStrategy(RoutingStrategy):
    """
    Baseline Strategy: The Naive Architecture.
    
    Routes 100% of requests directly to the expensive Frontier Model (e.g. GPT-4o / Claude Sonnet)
    without caching or decision evaluation.
    """
    name = "baseline"

    def __init__(self, frontier_provider: FrontierModelProvider = None):
        self.provider = frontier_provider or FrontierModelProvider()

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        start = time.perf_counter()
        resp = await self.provider.generate(request.prompt)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        telemetry = TelemetryTrace(
            request_id=f"base_{int(time.time()*1000)}",
            intent="unknown",
            complexity_score=2.0,
            jev_confidence=1.0,
            selected_route=RouteType.FRONTIER_MODEL,
            policy_reason="Baseline strategy: 100% routed directly to Frontier Model.",
            actual_model=resp.model_name,
            cache_hit=False,
            fallback_triggered=False,
            jev_latency_ms=0.0,
            model_latency_ms=round(resp.latency_ms, 2),
            gateway_overhead_ms=round(max(0.1, elapsed_ms - resp.latency_ms), 2),
            total_latency_ms=round(elapsed_ms, 2),
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            estimated_cost_usd=resp.cost_usd,
            baseline_cost_usd=resp.cost_usd,
            cost_saved_usd=0.0,
        )

        return GatewayResponse(
            request_id=telemetry.request_id,
            content=resp.content,
            route=RouteType.FRONTIER_MODEL,
            model=resp.model_name,
            telemetry=telemetry,
        )


class RuleBasedStrategy(RoutingStrategy):
    """
    Strategy A: Static Rule-Based Routing.
    
    Routes using simple keyword/regex pattern matching without Jev or calibrated confidence.
    """
    name = "rules"

    def __init__(
        self,
        frontier_provider: FrontierModelProvider = None,
        small_provider: SmallModelProvider = None,
        deterministic_provider: DeterministicProvider = None,
    ):
        self.frontier = frontier_provider or FrontierModelProvider()
        self.small = small_provider or SmallModelProvider()
        self.deterministic = deterministic_provider or DeterministicProvider()

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        start = time.perf_counter()
        lowered = request.prompt.lower().strip()

        # Heuristic rules
        if lowered in ("hello", "hi", "ping"):
            route = RouteType.DETERMINISTIC
            resp = await self.deterministic.generate(request.prompt)
            intent = "factual_question"
        elif any(k in lowered for k in ("why", "compare", "prove", "architecture", "tradeoff")):
            route = RouteType.FRONTIER_MODEL
            resp = await self.frontier.generate(request.prompt)
            intent = "reasoning"
        else:
            route = RouteType.SMALL_MODEL
            resp = await self.small.generate(request.prompt)
            intent = "general"

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        baseline_cost = self.frontier.estimate_cost(resp.input_tokens, resp.output_tokens)
        cost_saved = max(0.0, baseline_cost - resp.cost_usd)

        telemetry = TelemetryTrace(
            request_id=f"rule_{int(time.time()*1000)}",
            intent=intent,
            complexity_score=1.0,
            jev_confidence=0.70,
            selected_route=route,
            policy_reason="Static keyword heuristic route match.",
            actual_model=resp.model_name,
            cache_hit=False,
            fallback_triggered=False,
            jev_latency_ms=0.0,
            model_latency_ms=round(resp.latency_ms, 2),
            gateway_overhead_ms=round(max(0.1, elapsed_ms - resp.latency_ms), 2),
            total_latency_ms=round(elapsed_ms, 2),
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            estimated_cost_usd=resp.cost_usd,
            baseline_cost_usd=baseline_cost,
            cost_saved_usd=round(cost_saved, 7),
        )

        return GatewayResponse(
            request_id=telemetry.request_id,
            content=resp.content,
            route=route,
            model=resp.model_name,
            telemetry=telemetry,
        )


class JevFlowStrategy(RoutingStrategy):
    """
    Strategy B: JevFlow Adaptive Gateway.
    
    Uses Pre-Decision Cache -> Jev System One Decisions -> Deterministic Policy -> Provider Execution.
    """
    name = "jevflow"

    def __init__(self, gateway_service: GatewayService):
        self.gateway = gateway_service

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        return await self.gateway.process_request(request)
