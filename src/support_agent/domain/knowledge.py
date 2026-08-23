"""Knowledge article and retrieval evidence models."""

from datetime import date
from typing import Annotated

from pydantic import Field, field_validator

from support_agent.domain.base import DomainModel
from support_agent.domain.common import KnowledgeStatus
from support_agent.domain.incident import Category

KnowledgeId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")]


class KnowledgeArticle(DomainModel):
    """A versioned support article available to the local repository."""

    knowledge_id: KnowledgeId
    title: Annotated[str, Field(min_length=1, max_length=200)]
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    category: Category
    tags: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list,
        max_length=20,
    )
    status: KnowledgeStatus
    updated_at: date

    @field_validator("tags")
    @classmethod
    def normalize_unique_tags(cls, tags: list[str]) -> list[str]:
        """Normalize tags and reject duplicates that add no retrieval signal."""

        normalized = [tag.casefold() for tag in tags]
        if len(normalized) != len(set(normalized)):
            raise ValueError("tags must be unique, ignoring case")
        return normalized


class Evidence(DomainModel):
    """Explainable result returned by the knowledge retriever."""

    knowledge_id: KnowledgeId
    title: Annotated[str, Field(min_length=1, max_length=200)]
    score: Annotated[float, Field(ge=0.0, le=1.0)]
    matched_terms: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
        max_length=50,
    )
    status: KnowledgeStatus
    updated_at: date

    @field_validator("matched_terms")
    @classmethod
    def normalize_unique_terms(cls, terms: list[str]) -> list[str]:
        """Return normalized unique terms for consistent explanations."""

        normalized = [term.casefold() for term in terms]
        return list(dict.fromkeys(normalized))

