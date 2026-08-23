"""Deterministic and explainable weighted lexical retrieval."""

import math
import re
from dataclasses import dataclass

from support_agent.domain.incident import Incident
from support_agent.domain.knowledge import Evidence, KnowledgeArticle
from support_agent.domain.ports import KnowledgeRepository

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# These words carry little diagnostic value in the small English demo corpus.
STOP_WORDS = frozenset(
    {
        "a",
        "after",
        "all",
        "and",
        "are",
        "as",
        "at",
        "be",
        "before",
        "but",
        "by",
        "can",
        "cannot",
        "contains",
        "could",
        "demo",
        "did",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "knowledge",
        "less",
        "message",
        "no",
        "not",
        "of",
        "on",
        "only",
        "or",
        "procedure",
        "reports",
        "request",
        "set",
        "should",
        "so",
        "than",
        "that",
        "the",
        "their",
        "this",
        "through",
        "to",
        "user",
        "when",
        "with",
        "without",
    }
)


def tokenize(text: str) -> frozenset[str]:
    """Normalize an English support string into unique diagnostic terms."""

    return frozenset(
        token
        for token in TOKEN_PATTERN.findall(text.casefold())
        if token not in STOP_WORDS and len(token) > 1
    )


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    """Stable scoring policy for the Phase 4 retriever."""

    title_weight: float = 0.40
    tags_weight: float = 0.35
    content_weight: float = 0.20
    category_bonus: float = 0.05
    minimum_score: float = 0.08

    def __post_init__(self) -> None:
        total = self.title_weight + self.tags_weight + self.content_weight
        if not math.isclose(total + self.category_bonus, 1.0):
            raise ValueError("retrieval weights and category bonus must total 1.0")
        if not 0.0 <= self.minimum_score <= 1.0:
            raise ValueError("minimum_score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class _ScoredArticle:
    article: KnowledgeArticle
    score: float
    matched_terms: tuple[str, ...]


class WeightedLexicalRetriever:
    """Rank published articles using field-level term coverage."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._repository = repository
        self._config = config or RetrievalConfig()

    def search(self, incident: Incident, *, limit: int = 3) -> list[Evidence]:
        """Return deterministic Top-N evidence with normalized matched terms."""

        if limit < 1:
            raise ValueError("limit must be at least 1")

        query_terms = tokenize(f"{incident.short_description} {incident.description}")
        if not query_terms:
            return []

        scored = [
            result
            for article in self._repository.list_published()
            if (result := self._score(article, incident, query_terms)).score
            >= self._config.minimum_score
        ]
        scored.sort(key=lambda item: (-item.score, item.article.knowledge_id))

        return [
            Evidence(
                knowledge_id=item.article.knowledge_id,
                title=item.article.title,
                score=item.score,
                matched_terms=list(item.matched_terms),
                status=item.article.status,
                updated_at=item.article.updated_at,
            )
            for item in scored[:limit]
        ]

    def _score(
        self,
        article: KnowledgeArticle,
        incident: Incident,
        query_terms: frozenset[str],
    ) -> _ScoredArticle:
        title_terms = tokenize(article.title)
        tag_terms = tokenize(" ".join(article.tags))
        content_terms = tokenize(article.content)

        title_overlap = query_terms & title_terms
        tag_overlap = query_terms & tag_terms
        content_overlap = query_terms & content_terms
        matched_terms = tuple(sorted(title_overlap | tag_overlap | content_overlap))

        score = (
            self._config.title_weight * self._coverage(title_overlap, query_terms)
            + self._config.tags_weight * self._coverage(tag_overlap, query_terms)
            + self._config.content_weight * self._coverage(content_overlap, query_terms)
        )
        if incident.category and incident.category.casefold() == article.category.casefold():
            score += self._config.category_bonus

        return _ScoredArticle(
            article=article,
            score=round(min(score, 1.0), 4),
            matched_terms=matched_terms,
        )

    @staticmethod
    def _coverage(overlap: frozenset[str], query_terms: frozenset[str]) -> float:
        """Measure how much of the incident vocabulary a field explains."""

        return len(overlap) / len(query_terms)

