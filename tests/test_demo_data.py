"""Validate the fictional Phase 3 dataset and its evaluation contract."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from support_agent.domain import Incident, KnowledgeArticle, KnowledgeStatus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def load_json(filename: str) -> Any:
    """Load a project JSON fixture as UTF-8."""

    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def test_all_demo_incidents_are_unique_and_valid() -> None:
    incidents = [Incident.model_validate(item) for item in load_json("incidents.json")]
    incident_ids = [incident.incident_id for incident in incidents]

    assert len(incidents) == 8
    assert len(incident_ids) == len(set(incident_ids))
    assert all(incident_id.startswith("INC-DEMO-") for incident_id in incident_ids)


def test_all_demo_knowledge_articles_are_unique_and_valid() -> None:
    articles = [
        KnowledgeArticle.model_validate(item) for item in load_json("knowledge.json")
    ]
    knowledge_ids = [article.knowledge_id for article in articles]

    assert 8 <= len(articles) <= 12
    assert len(knowledge_ids) == len(set(knowledge_ids))
    assert all(knowledge_id.startswith("KB-DEMO-") for knowledge_id in knowledge_ids)
    assert {article.status for article in articles} == {
        KnowledgeStatus.DRAFT,
        KnowledgeStatus.PUBLISHED,
        KnowledgeStatus.RETIRED,
    }


def test_gold_cases_cover_every_incident_and_required_case_type() -> None:
    incident_ids = {item["incident_id"] for item in load_json("incidents.json")}
    gold = load_json("gold_cases.json")
    cases = gold["cases"]

    assert gold["schema_version"] == "1.0"
    assert {case["incident_id"] for case in cases} == incident_ids
    assert {case["case_type"] for case in cases} == {
        "primary",
        "ambiguous",
        "insufficient_context",
        "no_match",
        "stale_knowledge",
        "high_risk",
    }


def test_gold_knowledge_references_exist_and_never_target_nonpublished_articles() -> None:
    articles = {
        article.knowledge_id: article
        for article in (
            KnowledgeArticle.model_validate(item) for item in load_json("knowledge.json")
        )
    }
    cases = load_json("gold_cases.json")["cases"]

    for case in cases:
        referenced_ids = set(case["relevant_knowledge_ids"])
        expected_top_id = case["expected_top_knowledge_id"]

        assert referenced_ids <= articles.keys()
        assert all(
            articles[knowledge_id].status is KnowledgeStatus.PUBLISHED
            for knowledge_id in referenced_ids
        )
        if expected_top_id is not None:
            assert expected_top_id in referenced_ids


def test_no_match_case_has_no_expected_evidence_and_requires_abstention() -> None:
    cases = load_json("gold_cases.json")["cases"]
    no_match = next(case for case in cases if case["case_type"] == "no_match")

    assert no_match["relevant_knowledge_ids"] == []
    assert no_match["expected_top_knowledge_id"] is None
    assert no_match["should_abstain"] is True
    assert no_match["expected_grounded"] is False


def test_stale_case_matches_article_older_than_fixed_freshness_limit() -> None:
    gold = load_json("gold_cases.json")
    reference_date = date.fromisoformat(gold["freshness_reference_date"])
    cutoff = reference_date - timedelta(days=gold["freshness_max_age_days"])
    articles = {
        article.knowledge_id: article
        for article in (
            KnowledgeArticle.model_validate(item) for item in load_json("knowledge.json")
        )
    }
    stale_case = next(case for case in gold["cases"] if case["case_type"] == "stale_knowledge")

    assert stale_case["should_abstain"] is True
    assert stale_case["expected_knowledge_fresh"] is False
    assert all(
        articles[knowledge_id].updated_at < cutoff
        for knowledge_id in stale_case["relevant_knowledge_ids"]
    )


def test_high_risk_cases_are_explicit_and_retain_human_approval_boundary() -> None:
    cases = load_json("gold_cases.json")["cases"]
    high_risk_cases = [case for case in cases if case["high_risk_action"]]

    assert {case["incident_id"] for case in high_risk_cases} == {
        "INC-DEMO-007",
        "INC-DEMO-008",
    }
    assert all(case["expected_priority"] in {"P1", "P3"} for case in high_risk_cases)


def test_fixtures_use_only_demo_identifiers() -> None:
    serialized = "\n".join(
        (DATA_DIR / filename).read_text(encoding="utf-8")
        for filename in ("incidents.json", "knowledge.json", "gold_cases.json")
    )

    assert "@" not in serialized
    assert "http://" not in serialized
    assert "https://" not in serialized

