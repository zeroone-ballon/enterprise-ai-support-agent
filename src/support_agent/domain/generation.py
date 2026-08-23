"""Structured recommendation generation and provenance models."""

from typing import Annotated, Literal

from pydantic import Field

from support_agent.domain.base import DomainModel
from support_agent.domain.knowledge import KnowledgeId


class GeneratedDraft(DomainModel):
    """Strict provider output accepted before policy guardrails."""

    summary: Annotated[str, Field(min_length=1, max_length=500)]
    suggested_response: Annotated[str, Field(min_length=1, max_length=4000)]
    next_actions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1,
        max_length=20,
    )
    cited_knowledge_ids: list[KnowledgeId] = Field(min_length=1, max_length=3)


class GenerationMetadata(DomainModel):
    """Expose how a recommendation was generated and whether fallback occurred."""

    mode: Literal["deterministic", "llm"] = "deterministic"
    provider: Annotated[str, Field(min_length=1, max_length=120)] = "deterministic"
    fallback_used: bool = False
    violations: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list,
        max_length=20,
    )
