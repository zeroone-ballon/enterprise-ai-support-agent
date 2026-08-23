"""External data and action adapters."""

from support_agent.adapters.in_memory_lifecycle_repository import (
    DuplicateRecommendationError,
    InMemoryLifecycleRepository,
    RecommendationNotFoundError,
)
from support_agent.adapters.json_knowledge_repository import (
    JsonKnowledgeRepository,
    KnowledgeDataError,
)

__all__ = [
    "DuplicateRecommendationError",
    "InMemoryLifecycleRepository",
    "JsonKnowledgeRepository",
    "KnowledgeDataError",
    "RecommendationNotFoundError",
]
