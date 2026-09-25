import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_factory
from backend.app.db.models import RequestRecord
from backend.app.schemas.response import TelemetryTrace
from backend.app.telemetry.metrics import compute_telemetry_aggregations

logger = logging.getLogger("jevflow.telemetry_repo")


class TelemetryRepository:
    """Repository handling database persistence and aggregation queries for telemetry traces."""

    async def save_trace(self, trace: TelemetryTrace) -> None:
        """Persist a single telemetry trace asynchronously."""
        async with async_session_factory() as session:
            try:
                record = RequestRecord(
                    request_id=trace.request_id,
                    timestamp=trace.timestamp,
                    intent=trace.intent,
                    complexity_score=trace.complexity_score,
                    jev_confidence=trace.jev_confidence,
                    selected_route=trace.selected_route.value if hasattr(trace.selected_route, "value") else str(trace.selected_route),
                    policy_reason=trace.policy_reason,
                    actual_model=trace.actual_model,
                    cache_hit=trace.cache_hit,
                    fallback_triggered=trace.fallback_triggered,
                    fallback_reason=trace.fallback_reason,
                    retries_attempted=trace.retries_attempted,
                    circuit_breaker_tripped=trace.circuit_breaker_tripped,
                    error_category=trace.error_category,
                    jev_latency_ms=trace.jev_latency_ms,
                    model_latency_ms=trace.model_latency_ms,
                    gateway_overhead_ms=trace.gateway_overhead_ms,
                    total_latency_ms=trace.total_latency_ms,
                    input_tokens=trace.input_tokens,
                    output_tokens=trace.output_tokens,
                    estimated_cost_usd=trace.estimated_cost_usd,
                    baseline_cost_usd=trace.baseline_cost_usd,
                    cost_saved_usd=trace.cost_saved_usd,
                )
                session.add(record)
                await session.commit()
            except Exception as exc:
                logger.error("Failed to persist telemetry trace %s: %s", trace.request_id, exc)
                await session.rollback()

    async def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        route: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List historical request traces with pagination and route filtering."""
        async with async_session_factory() as session:
            stmt = select(RequestRecord).order_by(desc(RequestRecord.timestamp))
            if route:
                stmt = stmt.where(RequestRecord.selected_route == route)
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            records = result.scalars().all()
            return [
                {
                    "request_id": r.request_id,
                    "timestamp": r.timestamp.isoformat(),
                    "intent": r.intent,
                    "complexity_score": r.complexity_score,
                    "jev_confidence": r.jev_confidence,
                    "selected_route": r.selected_route,
                    "policy_reason": r.policy_reason,
                    "actual_model": r.actual_model,
                    "cache_hit": r.cache_hit,
                    "fallback_triggered": r.fallback_triggered,
                    "fallback_reason": r.fallback_reason,
                    "retries_attempted": r.retries_attempted,
                    "circuit_breaker_tripped": r.circuit_breaker_tripped,
                    "error_category": r.error_category,
                    "jev_latency_ms": r.jev_latency_ms,
                    "model_latency_ms": r.model_latency_ms,
                    "gateway_overhead_ms": r.gateway_overhead_ms,
                    "total_latency_ms": r.total_latency_ms,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "estimated_cost_usd": r.estimated_cost_usd,
                    "baseline_cost_usd": r.baseline_cost_usd,
                    "cost_saved_usd": r.cost_saved_usd,
                }
                for r in records
            ]

    async def get_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single trace with waterfall breakdown."""
        async with async_session_factory() as session:
            stmt = select(RequestRecord).where(RequestRecord.request_id == request_id)
            result = await session.execute(stmt)
            r = result.scalar_one_or_none()
            if not r:
                return None
            return {
                "request_id": r.request_id,
                "timestamp": r.timestamp.isoformat(),
                "intent": r.intent,
                "complexity_score": r.complexity_score,
                "jev_confidence": r.jev_confidence,
                "selected_route": r.selected_route,
                "policy_reason": r.policy_reason,
                "actual_model": r.actual_model,
                "cache_hit": r.cache_hit,
                "fallback_triggered": r.fallback_triggered,
                "fallback_reason": r.fallback_reason,
                "retries_attempted": r.retries_attempted,
                "circuit_breaker_tripped": r.circuit_breaker_tripped,
                "error_category": r.error_category,
                "waterfall": {
                    "jev_decision_ms": r.jev_latency_ms,
                    "model_execution_ms": r.model_latency_ms,
                    "gateway_overhead_ms": r.gateway_overhead_ms,
                    "total_end_to_end_ms": r.total_latency_ms,
                },
                "economics": {
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "estimated_cost_usd": r.estimated_cost_usd,
                    "baseline_cost_usd": r.baseline_cost_usd,
                    "cost_saved_usd": r.cost_saved_usd,
                },
            }

    async def get_summary_metrics(self, limit: int = 1000) -> Dict[str, Any]:
        """Aggregate metrics (P50/P95/P99 latency, cost savings, route distributions)."""
        async with async_session_factory() as session:
            stmt = select(RequestRecord).order_by(desc(RequestRecord.timestamp)).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return compute_telemetry_aggregations(records)
