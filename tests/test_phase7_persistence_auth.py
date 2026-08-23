"""Phase 7 durability, authorization, and idempotency tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from support_agent.config import Settings
from support_agent.main import create_app

REVIEWER = {"X-API-Key": "dev-reviewer-key"}
EXECUTOR = {"X-API-Key": "dev-executor-key", "Idempotency-Key": "stable-key-0001"}
AUDITOR = {"X-API-Key": "dev-auditor-key"}


def payload(incident_id: str) -> dict[str, str]:
    return {
        "incident_id": incident_id,
        "short_description": "VPN account locked after repeated sign-in attempts",
        "description": "The corporate VPN reports that the account is locked.",
        "category": "access",
        "priority": "P3",
    }


def test_state_survives_app_restart_and_execution_retry_is_idempotent(tmp_path: Path) -> None:
    settings = Settings(lifecycle_db_path=tmp_path / "durable.db")
    first_app = TestClient(create_app(settings))
    created = first_app.post("/assist", json=payload("INC-PERSIST-001")).json()
    recommendation_id = created["recommendation_id"]
    first_app.post(
        f"/recommendations/{recommendation_id}/approve",
        json={"reviewer": "service-desk-lead", "reason": "verified"},
        headers=REVIEWER,
    )
    first_execution = first_app.post(
        f"/recommendations/{recommendation_id}/execute",
        json={"executor": "automation-operator"},
        headers=EXECUTOR,
    )
    assert first_execution.status_code == 200

    restarted_app = TestClient(create_app(settings))
    restored = restarted_app.get(
        f"/recommendations/{recommendation_id}", headers=AUDITOR
    )
    assert restored.json()["approval"]["status"] == "executed"

    retry = restarted_app.post(
        f"/recommendations/{recommendation_id}/execute",
        json={"executor": "automation-operator"},
        headers=EXECUTOR,
    )
    assert retry.status_code == 200
    assert retry.json() == first_execution.json()

    audit = restarted_app.get(
        f"/recommendations/{recommendation_id}/audit", headers=AUDITOR
    ).json()
    assert len(audit) == 3


def test_lifecycle_endpoints_enforce_credentials_roles_and_actor(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "auth.db")))
    recommendation_id = client.post("/assist", json=payload("INC-AUTH-001")).json()[
        "recommendation_id"
    ]
    path = f"/recommendations/{recommendation_id}/approve"
    decision = {"reviewer": "service-desk-lead"}

    assert client.post(path, json=decision).status_code == 401
    assert client.post(path, json=decision, headers=EXECUTOR).status_code == 403
    assert client.post(
        path,
        json={"reviewer": "someone-else"},
        headers=REVIEWER,
    ).status_code == 403


def test_execute_requires_idempotency_key(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "key.db")))
    recommendation_id = client.post("/assist", json=payload("INC-KEY-001")).json()[
        "recommendation_id"
    ]
    client.post(
        f"/recommendations/{recommendation_id}/approve",
        json={"reviewer": "service-desk-lead"},
        headers=REVIEWER,
    )

    response = client.post(
        f"/recommendations/{recommendation_id}/execute",
        json={"executor": "automation-operator"},
        headers={"X-API-Key": "dev-executor-key"},
    )

    assert response.status_code == 422
