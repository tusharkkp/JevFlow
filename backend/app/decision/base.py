from abc import ABC, abstractmethod
from backend.app.schemas.decision import DecisionResult


class DecisionEngine(ABC):
    """Abstract interface for System One probabilistic decision engines."""

    @abstractmethod
    async def evaluate(self, prompt: str) -> DecisionResult:
        """
        Evaluate the user prompt and return a structured decision result.
        
        Args:
            prompt: The text content of the request.
            
        Returns:
            DecisionResult containing intent, complexity, safety, and confidence.
        """
        pass
