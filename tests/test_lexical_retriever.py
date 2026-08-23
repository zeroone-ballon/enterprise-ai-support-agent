"""Tests for deterministic, explainable, and publication-safe retrieval."""

import json
from pathlib import Path

import pytest

from support_agent.adapters import JsonKnowledgeRepository
from support_agent.domain import Incident
from support_agent.services import (
    RetrievalConfig,
    WeightedLexicalRetriever,
    evaluate_retriever,
)
from support_agent.services.lexical_retriever import tokenize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def load_incidents() -> list[Incident]:
    return [
        Incident.model_validate(item)
        for item in json.loads((DATA_DIR / "incidents.json").read_text(encoding="utf-8"))
    ]


@pytest.fixture
def retriever() -> WeightedLexicalRetriever:
    repository = JsonKnowledgeRepository.from_path(DATA_DIR / "knowledge.json")
    return WeightedLexicalRetriever(repository)


def test_tokenization_normalizes_compounds_and_removes_stop_words() -> None:
    assert tokenize("The Microsoft-365 sign-in issue") == {
        "microsoft",
        "365",
        "sign",
        "issue",
    }


def test_retrieval_is_ranked_explainable_and_score_bounded(
    retriever: WeightedLexicalRetriever,
) -> None:
    incident = next(item for item in load_incidents() if item.incident_id == "INC-DEMO-001")

    evidence = retriever.search(incident)

    assert evidence[0].knowledge_id == "KB-DEMO-001"
    assert evidence[0].matched_terms
    assert "locked" in evidence[0].matched_terms
    assert all(0.0 <= item.score <= 1.0 for item in evidence)
    assert evidence == retriever.search(incident)


def test_retrieval_excludes_draft_and_retired_articles(
    retriever: WeightedLexicalRetriever,
) -> None:
    retrieved_ids = {
        item.knowledge_id for incident in load_incidents() for item in retriever.search(incident)
    }

    assert "KB-DEMO-010" not in retrieved_ids
    assert "KB-DEMO-011" not in retrieved_ids


def test_retrieval_returns_empty_for_deliberate_no_match(
    retriever: WeightedLexicalRetriever,
) -> None:
    incident = next(item for item in load_incidents() if item.incident_id == "INC-DEMO-006")

    assert retriever.search(incident) == []


def test_retrieval_limit_and_invalid_limit(retriever: WeightedLexicalRetriever) -> None:
    incident = next(item for item in load_incidents() if item.incident_id == "INC-DEMO-004")

    assert len(retriever.search(incident, limit=1)) == 1
    with pytest.raises(ValueError, match="at least 1"):
        retriever.search(incident, limit=0)


def test_empty_diagnostic_vocabulary_returns_no_evidence(
    retriever: WeightedLexicalRetriever,
) -> None:
    incident = Incident(
        incident_id="INC-EMPTY-VOCAB",
        short_description="The user is in the set",
        description="This is a request that should be in the set",
    )

    assert retriever.search(incident) == []


def test_config_rejects_invalid_weights_and_threshold() -> None:
    with pytest.raises(ValueError, match="must total 1.0"):
        RetrievalConfig(title_weight=0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        RetrievalConfig(minimum_score=1.1)


def test_gold_dataset_retrieval_metrics(retriever: WeightedLexicalRetriever) -> None:
    gold = json.loads((DATA_DIR / "gold_cases.json").read_text(encoding="utf-8"))

    metrics = evaluate_retriever(retriever, load_incidents(), gold["cases"])

    assert metrics.top1_accuracy >= 0.70
    assert metrics.top3_recall >= 0.90
    assert metrics.no_match_accuracy == 1.0
