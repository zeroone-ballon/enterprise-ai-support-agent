"""Tests for strict local JSON knowledge loading."""

import json
from pathlib import Path

import pytest

from support_agent.adapters import JsonKnowledgeRepository, KnowledgeDataError
from support_agent.domain import KnowledgeStatus

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_repository_loads_all_articles_but_lists_only_published() -> None:
    repository = JsonKnowledgeRepository.from_path(PROJECT_ROOT / "data/knowledge.json")

    published = repository.list_published()

    assert len(published) == 9
    assert all(article.status is KnowledgeStatus.PUBLISHED for article in published)
    assert repository.get("KB-DEMO-010").status is KnowledgeStatus.RETIRED  # type: ignore[union-attr]
    assert repository.get("KB-DEMO-011").status is KnowledgeStatus.DRAFT  # type: ignore[union-attr]
    assert repository.get("KB-UNKNOWN") is None


def test_repository_rejects_missing_invalid_and_nonarray_files(tmp_path: Path) -> None:
    with pytest.raises(KnowledgeDataError, match="unable to read"):
        JsonKnowledgeRepository.from_path(tmp_path / "missing.json")

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("[", encoding="utf-8")
    with pytest.raises(KnowledgeDataError, match="invalid JSON"):
        JsonKnowledgeRepository.from_path(invalid_json)

    object_root = tmp_path / "object.json"
    object_root.write_text("{}", encoding="utf-8")
    with pytest.raises(KnowledgeDataError, match="root must be an array"):
        JsonKnowledgeRepository.from_path(object_root)


def test_repository_rejects_invalid_articles_and_duplicate_ids(tmp_path: Path) -> None:
    invalid_article = tmp_path / "invalid-article.json"
    invalid_article.write_text('[{"knowledge_id":"KB-BROKEN"}]', encoding="utf-8")
    with pytest.raises(KnowledgeDataError, match="article validation failed"):
        JsonKnowledgeRepository.from_path(invalid_article)

    source = json.loads((PROJECT_ROOT / "data/knowledge.json").read_text(encoding="utf-8"))
    duplicate_file = tmp_path / "duplicate.json"
    duplicate_file.write_text(json.dumps([source[0], source[0]]), encoding="utf-8")
    with pytest.raises(KnowledgeDataError, match="IDs must be unique"):
        JsonKnowledgeRepository.from_path(duplicate_file)
