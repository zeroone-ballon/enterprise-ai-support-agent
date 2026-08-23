"""Thread-safe in-memory lifecycle storage for the Phase 6 PoC."""

from threading import RLock

from support_agent.domain import AssistResponse, AuditEvent


class DuplicateRecommendationError(ValueError):
    """Raised when a recommendation identifier already exists."""


class RecommendationNotFoundError(LookupError):
    """Raised when a lifecycle operation references an unknown recommendation."""


class InMemoryLifecycleRepository:
    """Store recommendation state and append-only audit events in process memory."""

    def __init__(self) -> None:
        self._recommendations: dict[str, AssistResponse] = {}
        self._events: dict[str, list[AuditEvent]] = {}
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
