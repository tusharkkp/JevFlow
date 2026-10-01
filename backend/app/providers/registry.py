import logging
from typing import Dict, Any, Optional, Tuple
from backend.app.core.config import settings
from backend.app.schemas.response import RouteType
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth
from backend.app.providers.deterministic_provider import DeterministicProvider
from backend.app.providers.small_model_provider import SmallModelProvider
from backend.app.providers.frontier_model_provider import FrontierModelProvider
from backend.app.providers.human_review_provider import HumanReviewProvider
from backend.app.providers.openai_provider import OpenAICompatibleProvider
from backend.app.providers.openrouter_jev_provider import OpenRouterJevProvider
from backend.app.reliability.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from backend.app.reliability.retry import retry_with_backoff

logger = logging.getLogger("jevflow.provider_registry")


class ProviderRegistry:
    """
    Registry and Execution Router for Model Providers with Circuit Breakers and Retries.
    """

    def __init__(
        self,
        deterministic_provider: Optional[ModelProvider] = None,
        small_model_provider: Optional[ModelProvider] = None,
        frontier_model_provider: Optional[ModelProvider] = None,
        human_review_provider: Optional[ModelProvider] = None,
    ):
        self.deterministic = deterministic_provider or DeterministicProvider()

        # Wire Real Provider if API key is set, else use simulated provider
        effective_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY

        if small_model_provider is not None:
            self.small_model = small_model_provider
        elif effective_key:
            if settings.SMALL_MODEL_NAME.startswith("typesafe/") or settings.SMALL_MODEL_NAME == "typesafe/jev-router":
                logger.info("Initializing OpenRouter Jev Router for Small Model (%s)", settings.SMALL_MODEL_NAME)
                self.small_model = OpenRouterJevProvider(
                    api_key=effective_key,
                    model_name=settings.SMALL_MODEL_NAME,
                    base_url=settings.OPENROUTER_BASE_URL or settings.OPENAI_BASE_URL,
                )
            else:
                logger.info("Initializing real Small Model Provider via %s (%s)", settings.OPENAI_BASE_URL, settings.SMALL_MODEL_NAME)
                self.small_model = OpenAICompatibleProvider(
                    api_key=effective_key,
                    model_name=settings.SMALL_MODEL_NAME,
                    base_url=settings.OPENAI_BASE_URL,
                    input_cost_per_million=settings.SMALL_MODEL_INPUT_COST_PER_M,
                    output_cost_per_million=settings.SMALL_MODEL_OUTPUT_COST_PER_M,
                )
        else:
            self.small_model = SmallModelProvider()

        if frontier_model_provider is not None:
            self.frontier_model = frontier_model_provider
        elif effective_key:
            if settings.FRONTIER_MODEL_NAME.startswith("typesafe/") or settings.FRONTIER_MODEL_NAME == "typesafe/jev-router":
                logger.info("Initializing OpenRouter Jev Router for Frontier Model (%s)", settings.FRONTIER_MODEL_NAME)
                self.frontier_model = OpenRouterJevProvider(
                    api_key=effective_key,
                    model_name=settings.FRONTIER_MODEL_NAME,
                    base_url=settings.OPENROUTER_BASE_URL or settings.OPENAI_BASE_URL,
                )
            else:
                logger.info("Initializing real Frontier Model Provider via %s (%s)", settings.OPENAI_BASE_URL, settings.FRONTIER_MODEL_NAME)
                self.frontier_model = OpenAICompatibleProvider(
                    api_key=effective_key,
                    model_name=settings.FRONTIER_MODEL_NAME,
                    base_url=settings.OPENAI_BASE_URL,
                    input_cost_per_million=settings.FRONTIER_MODEL_INPUT_COST_PER_M,
                    output_cost_per_million=settings.FRONTIER_MODEL_OUTPUT_COST_PER_M,
                )
        else:
            self.frontier_model = FrontierModelProvider()

        self.human_review = human_review_provider or HumanReviewProvider()

        # Primary mapping: RouteType -> ModelProvider
        self._routes: Dict[RouteType, ModelProvider] = {
            RouteType.DETERMINISTIC: self.deterministic,
            RouteType.SMALL_MODEL: self.small_model,
            RouteType.FRONTIER_MODEL: self.frontier_model,
            RouteType.HUMAN_REVIEW: self.human_review,
            RouteType.FALLBACK: self.small_model,
            RouteType.CACHE: self.deterministic,
        }

        # Circuit breakers per execution tier
        self.circuit_breakers: Dict[RouteType, CircuitBreaker] = {
            RouteType.FRONTIER_MODEL: CircuitBreaker("provider_frontier", failure_threshold=2, recovery_timeout_sec=5.0),
            RouteType.SMALL_MODEL: CircuitBreaker("provider_small", failure_threshold=3, recovery_timeout_sec=5.0),
            RouteType.DETERMINISTIC: CircuitBreaker("provider_deterministic", failure_threshold=5, recovery_timeout_sec=5.0),
            RouteType.HUMAN_REVIEW: CircuitBreaker("provider_review", failure_threshold=5, recovery_timeout_sec=5.0),
        }

    def get_provider(self, route: RouteType) -> ModelProvider:
        """Retrieve the primary provider assigned to an execution route."""
        return self._routes.get(route, self.small_model)

    async def execute_route(
        self,
        route: RouteType,
        prompt: str,
    ) -> Tuple[ProviderResponse, bool, Optional[str], int, bool, Optional[str]]:
        """
        Execute generation against the primary provider with Circuit Breakers, Retries, and Failover.
        
        Returns:
            Tuple of:
            (ProviderResponse, fallback_triggered, fallback_reason, retries_attempted, circuit_tripped, error_category)
        """
        primary = self.get_provider(route)
        cb = self.circuit_breakers.get(route)
        total_retries = 0

        try:
            # Execute with circuit breaker and retry
            if cb:
                async def _call():
                    resp, retries = await retry_with_backoff(
                        primary.generate,
                        max_retries=1,
                        base_delay_ms=20.0,
                        prompt=prompt,
                    )
                    return resp, retries

                resp, total_retries = await cb.call(_call)
            else:
                resp = await primary.generate(prompt)

            return resp, False, None, total_retries, False, None

        except CircuitBreakerOpenException as exc:
            logger.warning("Provider circuit breaker OPEN for '%s'; failing fast to backup.", route.value)
            fallback_provider = self.small_model if route == RouteType.FRONTIER_MODEL else self.deterministic
            fallback_resp = await fallback_provider.generate(prompt)
            return fallback_resp, True, "provider_circuit_breaker_open", 0, True, "circuit_breaker_open"

        except Exception as exc:
            logger.error(
                "Primary provider '%s' failed for route '%s' after retries: %s. Initiating failover.",
                primary.metadata.get("model_name"),
                route.value,
                exc,
            )
            # Automatic failover chain
            fallback_provider = self.small_model if route == RouteType.FRONTIER_MODEL else self.deterministic
            fallback_resp = await fallback_provider.generate(prompt)
            return fallback_resp, True, f"provider_failure: {str(exc)}", 1, False, "provider_error"

    def get_all_metadata(self) -> Dict[str, Any]:
        """Return catalog of all registered providers and their pricing/latency profiles."""
        return {
            "providers": {
                "deterministic": self.deterministic.metadata,
                "small_model": self.small_model.metadata,
                "frontier_model": self.frontier_model.metadata,
                "human_review": self.human_review.metadata,
            },
            "circuit_breakers": {
                k.value: v.get_status() for k, v in self.circuit_breakers.items()
            }
        }

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        """Perform parallel health checks across all providers."""
        return {
            "deterministic": await self.deterministic.health(),
            "small_model": await self.small_model.health(),
            "frontier_model": await self.frontier_model.health(),
            "human_review": await self.human_review.health(),
        }
