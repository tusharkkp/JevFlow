from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    FACTUAL_QUESTION = "factual_question"
    CODING = "coding"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    DATA_ANALYSIS = "data_analysis"
    CREATIVE = "creative"
    OTHER = "other"


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class RouteRecommendation(str, Enum):
    DETERMINISTIC = "deterministic"
    CACHE = "cache"
    SMALL_MODEL = "small_model"
    FRONTIER_MODEL = "frontier_model"
    HUMAN_REVIEW = "human_review"


class DecisionResult(BaseModel):
    """Normalized structured probabilistic decision produced by the System One layer."""
    intent: IntentType = Field(
        ...,
        description="Categorical intent of the request."
    )
    complexity_score: float = Field(
        ...,
        ge=0.0,
        le=2.0,
        description="Expected complexity score on an ordinal scale: 0.0 (simple) to 2.0 (complex)."
    )
    complexity_level: ComplexityLevel = Field(
        ...,
        description="Discretized complexity tier."
    )
    safety_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated probability (0 to 1) that the request is safe to execute automatically."
    )
    is_safe: bool = Field(
        ...,
        description="Boolean safety indicator based on the decision threshold."
    )
    recommended_route: RouteRecommendation = Field(
        ...,
        description="The execution route recommended by the probabilistic decision engine."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="System One confidence score for the primary classification."
    )
    decision_latency_ms: float = Field(
        ...,
        description="Latency in milliseconds taken to perform the System One decision."
    )
    model_used: str = Field(
        default="mock-system-one",
        description="Model identifier that served the decision."
    )
    raw_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed probabilities or raw answer dictionaries from the engine."
    )
