"""External data and action adapters."""

from support_agent.adapters.json_knowledge_repository import (
    JsonKnowledgeRepository,
    KnowledgeDataError,
)

__all__ = ["JsonKnowledgeRepository", "KnowledgeDataError"]

