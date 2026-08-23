"""Final release-candidate end-to-end acceptance tests."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent import __version__, demo
from support_agent.adapters import ServiceNowSandboxExecutor
from support_agent.config import Settings
from support_agent.main import create_app

REVIEWER = {"X-API-Key": "dev-reviewer-key"}
EXECUTOR = {"X-API-Key": "dev-executor-key", "Idempotency-Key": "phase11-rc-key"}
AUDITOR = {"X-API-Key": "dev-auditor-key"}


def test_release_candidate_end_to_end_contract(tmp_path: Path) -> None:
    database = tmp_path / "release-candidate.db"
    client = TestClient(create_app(Settings(app_env="test", lifecycle_db_path=database)))
    incident = {
        "incident_id": "INC-RC-ACCEPTANCE-001",
        "short_description": "VPN account locked after repeated sign-in attempts",
        "description": "The corporate VPN reports that the account is locked.",
        "category": "access",
        "priority": "P3",
    }

    created = client.post("/assist", json=incident)
    recommendation_id = created.json()["recommendation_id"]
    approved = client.post(
        f"/recommendations/{recommendation_id}/approve",
        headers=REVIEWER,
        json={"reviewer": "service-desk-lead", "reason": "acceptance evidence verified"},
    )
    executed = client.post(
        f"/recommendations/{recommendation_id}/execute",
        headers=EXECUTOR,
        json={"executor": "automation-operator"},
    )
    replayed = client.post(
        f"/recommendations/{recommendation_id}/execute",
        headers=EXECUTOR,
        json={"executor": "automation-operator"},
    )
    audit = client.get(f"/recommendations/{recommendation_id}/audit", headers=AUDITOR)

    assert created.status_code == approved.status_code == executed.status_code == 200
    assert approved.json()["approval"]["status"] == "approved"
    assert replayed.json() == executed.json()
    assert executed.json()["receipt"]["side_effects"] is False
    assert [event["event_type"] for event in audit.json()] == [
        "recommendation_created",
        "recommendation_approved",
        "mock_execution_completed",
    ]
    actions = ServiceNowSandboxExecutor(database).list_actions()
    assert len(actions) == 1
    assert actions[0].mode == "sandbox"


def test_release_candidate_version_is_exposed(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(app_env="test", lifecycle_db_path=tmp_path / "rc.db")))

    assert __version__ == "1.0.0rc1"
    assert client.get("/health").json()["version"] == "1.0.0rc1"
    assert client.get("/openapi.json").json()["info"]["version"] == "1.0.0rc1"


def test_live_demo_validates_idempotency_and_audit(monkeypatch) -> None:
    executed = {"receipt": {"status": "simulated", "side_effects": False}}
    responses = iter(
        [
            {
                "recommendation_id": "REC-INC-RC-DEMO",
                "evidence": [{"knowledge_id": "KB-DEMO-001"}],
                "generation": {"mode": "deterministic"},
            },
            {"approval": {"status": "approved"}},
            executed,
            executed,
            [
                {"event_type": "recommendation_created"},
                {"event_type": "recommendation_approved"},
                {"event_type": "mock_execution_completed"},
            ],
        ]
    )
    monkeypatch.setattr(demo, "_request", lambda *args, **kwargs: next(responses))

    summary = demo.run_demo(
        "http://testserver",
        "INC-RC-DEMO",
        "reviewer-key",
        "executor-key",
        "auditor-key",
    )

    assert summary["idempotent_replay"] is True
    assert summary["side_effects"] is False
    assert summary["audit_events"][-1] == "mock_execution_completed"


def test_live_demo_fails_closed_on_side_effect_claim(monkeypatch) -> None:
    executed = {"receipt": {"status": "simulated", "side_effects": True}}
    responses = iter(
        [
            {
                "recommendation_id": "REC-INC-RC-UNSAFE",
                "evidence": [],
                "generation": {"mode": "deterministic"},
            },
            {"approval": {"status": "approved"}},
            executed,
            executed,
            [
                {"event_type": "recommendation_created"},
                {"event_type": "recommendation_approved"},
                {"event_type": "mock_execution_completed"},
            ],
        ]
    )
    monkeypatch.setattr(demo, "_request", lambda *args, **kwargs: next(responses))

    with pytest.raises(RuntimeError, match="release-candidate assertions failed"):
        demo.run_demo("http://testserver", "INC-RC-UNSAFE", "reviewer", "executor", "auditor")


def test_live_demo_command_prints_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["support-agent-demo", "--incident-id", "INC-RC-CLI"])
    monkeypatch.setattr(
        demo,
        "run_demo",
        lambda *args: {"incident_id": "INC-RC-CLI", "side_effects": False},
    )

    assert demo.main() == 0
    assert '"side_effects": false' in capsys.readouterr().out
