"""Domain-facing repository and retrieval contracts."""

from typing import Protocol

from support_agent.domain.incident import Incident
from support_agent.domain.knowledge import Evidence, KnowledgeArticle


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

