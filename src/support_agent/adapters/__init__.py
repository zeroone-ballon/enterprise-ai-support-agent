"""External data and action adapters."""

from support_agent.adapters.in_memory_lifecycle_repository import (
    InMemoryLifecycleRepository,
)
from support_agent.adapters.json_knowledge_repository import (
    JsonKnowledgeRepository,
    KnowledgeDataError,
)
from support_agent.adapters.lifecycle_errors import (
    DuplicateRecommendationError,
    RecommendationNotFoundError,
)
from support_agent.adapters.servicenow_sandbox_executor import ServiceNowSandboxExecutor
from support_agent.adapters.sqlite_lifecycle_repository import SqliteLifecycleRepository

__all__ = [
    "DuplicateRecommendationError",
    "InMemoryLifecycleRepository",
    "JsonKnowledgeRepository",
    "KnowledgeDataError",
    "RecommendationNotFoundError",
    "SqliteLifecycleRepository",
    "ServiceNowSandboxExecutor",
]
