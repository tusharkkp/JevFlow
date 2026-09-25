from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RequestRecord(Base):
    """
    Persistent normalized telemetry record for every gateway request.
    
    Adheres strictly to the privacy invariant: Prompts and sensitive user data
    are NOT stored; only operational, latency, cost, and routing metadata.
    """
    __tablename__ = "requests"

    request_id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    
    # Classification & Decision
    intent = Column(String(64), nullable=False, index=True)
    complexity_score = Column(Float, nullable=False)
    jev_confidence = Column(Float, nullable=False)
    selected_route = Column(String(64), nullable=False, index=True)
    policy_reason = Column(Text, nullable=False)
    actual_model = Column(String(128), nullable=False, index=True)

    # Reliability & Cache
    cache_hit = Column(Boolean, default=False, nullable=False, index=True)
    fallback_triggered = Column(Boolean, default=False, nullable=False, index=True)
    fallback_reason = Column(String(256), nullable=True)
    retries_attempted = Column(Integer, default=0, nullable=False)
    circuit_breaker_tripped = Column(Boolean, default=False, nullable=False)
    error_category = Column(String(64), nullable=True)

    # Latencies (ms)
    jev_latency_ms = Column(Float, nullable=False)
    model_latency_ms = Column(Float, nullable=False)
    gateway_overhead_ms = Column(Float, nullable=False)
    total_latency_ms = Column(Float, nullable=False)

    # Token Economics ($)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    estimated_cost_usd = Column(Float, nullable=False)
    baseline_cost_usd = Column(Float, nullable=False)
    cost_saved_usd = Column(Float, nullable=False)


class ExperimentRecord(Base):
    """Aggregated benchmark experiment run comparing Baseline vs Rules vs JevFlow."""
    __tablename__ = "experiments"

    experiment_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    strategy = Column(String(64), nullable=False, index=True)  # 'baseline', 'rules', 'jevflow'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    total_requests = Column(Integer, nullable=False)
    p50_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    p99_latency_ms = Column(Float, nullable=False)
    average_latency_ms = Column(Float, nullable=False)
    
    total_cost_usd = Column(Float, nullable=False)
    cost_saved_usd = Column(Float, nullable=False)
    average_cost_per_request = Column(Float, nullable=False)
    
    success_rate = Column(Float, nullable=False)
    fallback_rate = Column(Float, nullable=False)
    cache_hit_rate = Column(Float, nullable=False)
    raw_results = Column(Text, nullable=True)
