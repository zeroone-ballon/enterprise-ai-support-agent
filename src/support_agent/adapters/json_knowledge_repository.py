"""Validated local JSON implementation of the knowledge repository."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from support_agent.domain.common import KnowledgeStatus
from support_agent.domain.knowledge import KnowledgeArticle


class KnowledgeDataError(ValueError):
    """Raised when a JSON knowledge source violates its data contract."""


class JsonKnowledgeRepository:
    """Load immutable knowledge articles from a UTF-8 JSON array."""

    def __init__(self, articles: tuple[KnowledgeArticle, ...]) -> None:
        ids = [article.knowledge_id for article in articles]
        if len(ids) != len(set(ids)):
            raise KnowledgeDataError("knowledge IDs must be unique")

        self._articles = articles
        self._by_id = {article.knowledge_id: article for article in articles}

    @classmethod
    def from_path(cls, path: str | Path) -> "JsonKnowledgeRepository":
        """Read and validate a repository without silently skipping bad records."""

        source_path = Path(path)
        try:
            raw: Any = json.loads(source_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise KnowledgeDataError(f"unable to read knowledge file: {source_path}") from error
        except json.JSONDecodeError as error:
            raise KnowledgeDataError(f"invalid JSON in knowledge file: {source_path}") from error

        if not isinstance(raw, list):
            raise KnowledgeDataError("knowledge JSON root must be an array")

        try:
            articles = tuple(KnowledgeArticle.model_validate(item) for item in raw)
        except ValidationError as error:
            raise KnowledgeDataError("knowledge article validation failed") from error

        return cls(articles)

    def list_published(self) -> tuple[KnowledgeArticle, ...]:
        """Exclude draft and retired articles from recommendation evidence."""

        return tuple(
            article for article in self._articles if article.status is KnowledgeStatus.PUBLISHED
        )

    def get(self, knowledge_id: str) -> KnowledgeArticle | None:
        """Return an article regardless of publication state for administration."""

        return self._by_id.get(knowledge_id)
