import logging
from typing import Dict, Any, Optional, Tuple
from backend.app.schemas.response import RouteType
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth
from backend.app.providers.deterministic_provider import DeterministicProvider
from backend.app.providers.small_model_provider import SmallModelProvider
from backend.app.providers.frontier_model_provider import FrontierModelProvider
from backend.app.providers.human_review_provider import HumanReviewProvider

logger = logging.getLogger("jevflow.provider_registry")


class ProviderRegistry:
    """
    Registry and Execution Router for Model Providers.
    
    Decouples the gateway from any single vendor, handles route-to-provider
    dispatch, and manages automatic failover chains.
    """

    def __init__(
        self,
        deterministic_provider: Optional[ModelProvider] = None,
        small_model_provider: Optional[ModelProvider] = None,
        frontier_model_provider: Optional[ModelProvider] = None,
        human_review_provider: Optional[ModelProvider] = None,
    ):
        self.deterministic = deterministic_provider or DeterministicProvider()
        self.small_model = small_model_provider or SmallModelProvider()
        self.frontier_model = frontier_model_provider or FrontierModelProvider()
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

    def get_provider(self, route: RouteType) -> ModelProvider:
        """Retrieve the primary provider assigned to an execution route."""
        return self._routes.get(route, self.small_model)

    async def execute_route(
        self,
        route: RouteType,
        prompt: str,
    ) -> Tuple[ProviderResponse, bool, Optional[str]]:
        """
        Execute generation against the primary provider with automatic failover.
        
        Returns:
            Tuple of (ProviderResponse, fallback_triggered: bool, fallback_reason: Optional[str])
        """
        primary = self.get_provider(route)
        try:
            resp = await primary.generate(prompt)
            return resp, False, None
        except Exception as exc:
            logger.error(
                "Primary provider '%s' failed for route '%s': %s. Initiating failover.",
                primary.metadata.get("model_name"),
                route.value,
                exc,
            )
            # Automatic failover chain:
            # If frontier fails -> failover to small model
            # If small model fails -> failover to deterministic engine
            if route == RouteType.FRONTIER_MODEL:
                fallback_provider = self.small_model
            else:
                fallback_provider = self.deterministic

            fallback_resp = await fallback_provider.generate(prompt)
            return fallback_resp, True, f"provider_failure: {str(exc)}"

    def get_all_metadata(self) -> Dict[str, Any]:
        """Return catalog of all registered providers and their pricing/latency profiles."""
        return {
            "providers": {
                "deterministic": self.deterministic.metadata,
                "small_model": self.small_model.metadata,
                "frontier_model": self.frontier_model.metadata,
                "human_review": self.human_review.metadata,
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
