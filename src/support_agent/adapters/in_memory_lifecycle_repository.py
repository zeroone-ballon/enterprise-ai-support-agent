"""Thread-safe in-memory lifecycle storage for the Phase 6 PoC."""

from threading import RLock

from support_agent.adapters.lifecycle_errors import (
    DuplicateRecommendationError,
    RecommendationNotFoundError,
)
from support_agent.domain import AssistResponse, AuditEvent
from support_agent.domain.lifecycle import ExecutionResult


class InMemoryLifecycleRepository:
    """Store recommendation state and append-only audit events in process memory."""

    def __init__(self) -> None:
        self._recommendations: dict[str, AssistResponse] = {}
        self._events: dict[str, list[AuditEvent]] = {}
        self._executions: dict[tuple[str, str], ExecutionResult] = {}
        self._lock = RLock()

    def create(self, response: AssistResponse) -> None:
        with self._lock:
            recommendation_id = response.recommendation_id
            if recommendation_id in self._recommendations:
                raise DuplicateRecommendationError(recommendation_id)
            self._recommendations[recommendation_id] = response.model_copy(deep=True)
            self._events[recommendation_id] = []

    def get(self, recommendation_id: str) -> AssistResponse:
        with self._lock:
            try:
                response = self._recommendations[recommendation_id]
            except KeyError as error:
                raise RecommendationNotFoundError(recommendation_id) from error
            return response.model_copy(deep=True)

    def save(self, response: AssistResponse) -> None:
        with self._lock:
            if response.recommendation_id not in self._recommendations:
                raise RecommendationNotFoundError(response.recommendation_id)
            self._recommendations[response.recommendation_id] = response.model_copy(deep=True)

    def append_event(self, event: AuditEvent) -> None:
        with self._lock:
            try:
                events = self._events[event.recommendation_id]
            except KeyError as error:
                raise RecommendationNotFoundError(event.recommendation_id) from error
            if event.sequence != len(events) + 1:
                raise ValueError("audit event sequence must be contiguous")
            events.append(event.model_copy(deep=True))

    def list_events(self, recommendation_id: str) -> list[AuditEvent]:
        with self._lock:
            try:
                events = self._events[recommendation_id]
            except KeyError as error:
                raise RecommendationNotFoundError(recommendation_id) from error
            return [event.model_copy(deep=True) for event in events]

    def get_execution(self, recommendation_id: str, idempotency_key: str) -> ExecutionResult | None:
        with self._lock:
            result = self._executions.get((recommendation_id, idempotency_key))
            return result.model_copy(deep=True) if result else None

    def save_execution(
        self,
        recommendation_id: str,
        idempotency_key: str,
        result: ExecutionResult,
    ) -> None:
        with self._lock:
            self._executions[(recommendation_id, idempotency_key)] = result.model_copy(deep=True)
