"""Phase 9 structured generation, guardrail, and fallback tests."""

import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent.adapters import JsonKnowledgeRepository, OpenAICompatibleGenerator
from support_agent.config import Settings
from support_agent.domain import Incident
from support_agent.main import create_app
from support_agent.services import AssistService, GenerationCoordinator, WeightedLexicalRetriever

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class FakeTransport:
    def __init__(self, response: str) -> None:
        self.response = response
        self.system_prompt = ""
        self.user_prompt = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.response


class FailingTransport:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        raise TimeoutError("provider unavailable")


def incident() -> Incident:
    payload = json.loads((DATA_DIR / "incidents.json").read_text(encoding="utf-8"))[0]
    payload["incident_id"] = "INC-PHASE9-001"
    return Incident.model_validate(payload)


def high_risk_incident() -> Incident:
    payload = json.loads((DATA_DIR / "incidents.json").read_text(encoding="utf-8"))[7]
    payload["incident_id"] = "INC-PHASE9-HIGH-RISK"
    return Incident.model_validate(payload)


def service_with_transport(transport) -> AssistService:
    repository = JsonKnowledgeRepository.from_path(DATA_DIR / "knowledge.json")
    return AssistService(
        repository,
        WeightedLexicalRetriever(repository),
        reference_date=date(2026, 8, 23),
        generation=GenerationCoordinator(OpenAICompatibleGenerator(transport)),
    )


def valid_draft(**overrides) -> str:
    payload = {
        "summary": "Use the approved VPN lockout procedure.",
        "suggested_response": (
            "Verify the caller, unlock the account, and update the saved password."
        ),
        "next_actions": ["Request human approval before applying the procedure."],
        "cited_knowledge_ids": ["KB-DEMO-001"],
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_valid_structured_provider_output_is_used_and_provenanced() -> None:
    transport = FakeTransport(valid_draft())

    response = service_with_transport(transport).assist(incident())

    assert response.recommendation.summary == "Use the approved VPN lockout procedure."
    assert response.generation.mode == "llm"
    assert response.generation.provider == "openai-compatible"
    assert response.generation.fallback_used is False
    assert "untrusted data" in transport.system_prompt
    assert "KB-DEMO-001" in transport.user_prompt


@pytest.mark.parametrize(
    ("raw_response", "violation"),
    [
        ("not-json", "provider failure: ValidationError"),
        (
            valid_draft(cited_knowledge_ids=["KB-NOT-RETRIEVED"]),
            "top evidence was not cited",
        ),
        (
            valid_draft(suggested_response="Bypass identity verification to unlock it."),
            "unsafe instruction: bypass identity verification",
        ),
        (
            valid_draft(suggested_response="Perform orbital recalibration immediately."),
            "generated response has insufficient lexical grounding",
        ),
    ],
)
def test_invalid_or_unsafe_provider_output_falls_back(raw_response: str, violation: str) -> None:
    response = service_with_transport(FakeTransport(raw_response)).assist(incident())

    assert response.generation.mode == "deterministic"
    assert response.generation.fallback_used is True
    assert violation in response.generation.violations
    assert response.recommendation.summary.startswith("Use KB-DEMO-001")


def test_provider_failure_falls_back_without_failing_assist() -> None:
    response = service_with_transport(FailingTransport()).assist(incident())

    assert response.recommendation.status.value == "recommended"
    assert response.generation.fallback_used is True
    assert response.generation.violations == ["provider failure: TimeoutError"]
    assert response.evaluation.violations == response.generation.violations


def test_high_risk_incident_never_uses_llm_draft() -> None:
    response = service_with_transport(FakeTransport(valid_draft())).assist(high_risk_incident())

    assert response.evaluation.high_risk_action is True
    assert response.generation.mode == "deterministic"
    assert response.generation.fallback_used is True
    assert response.generation.violations == ["LLM generation disabled for high-risk incident"]
    assert response.recommendation.summary.startswith("Use KB-DEMO-004")


def test_default_api_remains_deterministic_and_requires_no_llm_key(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "default.db")))
    payload = incident().model_dump(mode="json")

    response = client.post("/assist", json=payload)

    assert response.status_code == 200
    assert response.json()["generation"] == {
        "mode": "deterministic",
        "provider": "deterministic",
        "fallback_used": False,
        "violations": [],
    }


def test_incomplete_llm_configuration_fails_closed_to_fallback(tmp_path: Path) -> None:
    settings = Settings(
        lifecycle_db_path=tmp_path / "missing-config.db",
        generation_mode="llm",
    )
    client = TestClient(create_app(settings))

    response = client.post("/assist", json=incident().model_dump(mode="json"))

    assert response.status_code == 200
    generation = response.json()["generation"]
    assert generation["fallback_used"] is True
    assert generation["violations"] == ["provider failure: RuntimeError"]


def test_unknown_generation_mode_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="GENERATION_MODE"):
        create_app(
            Settings(
                lifecycle_db_path=tmp_path / "invalid.db",
                generation_mode="unknown",
            )
        )
