"""Domain-facing repository, retrieval, lifecycle, and execution contracts."""

from datetime import datetime
from typing import Protocol

from support_agent.domain.incident import Incident
from support_agent.domain.knowledge import Evidence, KnowledgeArticle
from support_agent.domain.lifecycle import (
    AuditEvent,
    ExecutionRequest,
    MockExecutionReceipt,
)
from support_agent.domain.response import AssistResponse


class KnowledgeRepository(Protocol):
    """Read-only knowledge source used by the application layer."""

    def list_published(self) -> tuple[KnowledgeArticle, ...]:
        """Return only articles eligible to support a recommendation."""

    def get(self, knowledge_id: str) -> KnowledgeArticle | None:
        """Return an article in any lifecycle state by ID."""


class Retriever(Protocol):
    """Find explainable evidence for an incident."""

    def search(self, incident: Incident, *, limit: int = 3) -> list[Evidence]:
        """Return ranked published evidence above the configured threshold."""


class LifecycleRepository(Protocol):
    """Persist current recommendation state and immutable audit events."""

    def create(self, response: AssistResponse) -> None: ...

    def get(self, recommendation_id: str) -> AssistResponse: ...

    def save(self, response: AssistResponse) -> None: ...

    def append_event(self, event: AuditEvent) -> None: ...

    def list_events(self, recommendation_id: str) -> list[AuditEvent]: ...


class ExecutionPort(Protocol):
    """Boundary behind which a safe execution adapter must live."""

    def execute(
        self,
        response: AssistResponse,
        request: ExecutionRequest,
        executed_at: datetime,
    ) -> MockExecutionReceipt: ...
