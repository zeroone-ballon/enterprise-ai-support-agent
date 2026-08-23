"""Gold-case tests for the Phase 5 assistance workflow."""

import json
from datetime import date
from pathlib import Path

import pytest

from support_agent.adapters import JsonKnowledgeRepository
from support_agent.domain import ApprovalStatus, Incident, RecommendationStatus
from support_agent.services import AssistService, WeightedLexicalRetriever

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def service() -> AssistService:
    repository = JsonKnowledgeRepository.from_path(DATA_DIR / "knowledge.json")
    return AssistService(
        repository,
        WeightedLexicalRetriever(repository),
        reference_date=date(2026, 8, 23),
    )


def test_assist_workflow_matches_all_gold_safety_outcomes(service: AssistService) -> None:
    incidents = {
        item["incident_id"]: Incident.model_validate(item) for item in load_json("incidents.json")
    }

    for case in load_json("gold_cases.json")["cases"]:
        response = service.assist(incidents[case["incident_id"]])

        assert response.classification.category == case["expected_category"]
        assert response.classification.priority == case["expected_priority"]
        assert response.evaluation.grounded is case["expected_grounded"]
        assert response.evaluation.knowledge_fresh is case["expected_knowledge_fresh"]
        assert response.evaluation.high_risk_action is case["high_risk_action"]
        assert response.approval.status is ApprovalStatus.PENDING
        assert (response.recommendation.status is RecommendationStatus.ABSTAINED) is case[
            "should_abstain"
        ]


def test_grounded_response_cites_evidence_and_remains_pending(service: AssistService) -> None:
    incident = Incident.model_validate(load_json("incidents.json")[0])

    response = service.assist(incident)

    assert response.recommendation.status is RecommendationStatus.RECOMMENDED
    assert response.evidence[0].knowledge_id == "KB-DEMO-001"
    assert response.confidence == response.evidence[0].score
    assert response.recommendation.suggested_response
    assert response.approval.status is ApprovalStatus.PENDING


def test_no_match_abstains_with_zero_confidence(service: AssistService) -> None:
    incident = Incident.model_validate(load_json("incidents.json")[5])

    response = service.assist(incident)

    assert response.recommendation.status is RecommendationStatus.ABSTAINED
    assert response.evidence == []
    assert response.confidence == 0.0
