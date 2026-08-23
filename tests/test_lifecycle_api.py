"""End-to-end HTTP tests for Phase 6 lifecycle controls."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from support_agent.config import Settings
from support_agent.main import create_app

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REVIEWER_HEADERS = {"X-API-Key": "dev-reviewer-key"}
EXECUTOR_HEADERS = {
    "X-API-Key": "dev-executor-key",
    "Idempotency-Key": "phase7-execution-key",
}
AUDITOR_HEADERS = {"X-API-Key": "dev-auditor-key"}


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "lifecycle.db")))


def incident(index: int, incident_id: str) -> dict:
    payload = json.loads((DATA_DIR / "incidents.json").read_text(encoding="utf-8"))[index]
    payload["incident_id"] = incident_id
    return payload


def test_approve_then_mock_execute_records_append_only_audit(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/assist", json=incident(0, "INC-PHASE6-001"))
    recommendation_id = created.json()["recommendation_id"]

    blocked = client.post(
        f"/recommendations/{recommendation_id}/execute",
        json={"executor": "automation-operator"},
        headers=EXECUTOR_HEADERS,
    )
    assert blocked.status_code == 409

    approved = client.post(
        f"/recommendations/{recommendation_id}/approve",
        json={"reviewer": "service-desk-lead", "reason": "Evidence verified"},
        headers=REVIEWER_HEADERS,
    )
    assert approved.status_code == 200
    assert approved.json()["approval"]["status"] == "approved"

    executed = client.post(
        f"/recommendations/{recommendation_id}/execute",
        json={"executor": "automation-operator"},
        headers=EXECUTOR_HEADERS,
    )
    assert executed.status_code == 200
    result = executed.json()
    assert result["recommendation"]["approval"]["status"] == "executed"
    assert result["receipt"]["status"] == "simulated"
    assert result["receipt"]["side_effects"] is False

    retrieved = client.get(f"/recommendations/{recommendation_id}", headers=AUDITOR_HEADERS)
    assert retrieved.json()["approval"]["status"] == "executed"

    audit = client.get(
        f"/recommendations/{recommendation_id}/audit", headers=AUDITOR_HEADERS
    ).json()
    assert [event["sequence"] for event in audit] == [1, 2, 3]
    assert [event["event_type"] for event in audit] == [
        "recommendation_created",
        "recommendation_approved",
        "mock_execution_completed",
    ]


def test_rejection_is_terminal_and_reason_is_audited(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/assist", json=incident(0, "INC-PHASE6-002"))
    recommendation_id = created.json()["recommendation_id"]

    rejected = client.post(
        f"/recommendations/{recommendation_id}/reject",
        json={"reviewer": "service-desk-lead", "reason": "Caller identity not verified"},
        headers=REVIEWER_HEADERS,
    )
    assert rejected.json()["approval"]["status"] == "rejected"

    execute = client.post(
        f"/recommendations/{recommendation_id}/execute",
        json={"executor": "automation-operator"},
        headers=EXECUTOR_HEADERS,
    )
    assert execute.status_code == 409

    audit = client.get(
        f"/recommendations/{recommendation_id}/audit", headers=AUDITOR_HEADERS
    ).json()
    assert audit[-1]["details"]["reason"] == "Caller identity not verified"


def test_abstained_recommendation_cannot_be_approved(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/assist", json=incident(5, "INC-PHASE6-003"))
    recommendation_id = created.json()["recommendation_id"]
    assert created.json()["recommendation"]["status"] == "abstained"

    response = client.post(
        f"/recommendations/{recommendation_id}/approve",
        json={"reviewer": "service-desk-lead"},
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "an abstained recommendation cannot be approved"


def test_duplicate_and_missing_recommendations_return_clear_errors(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    payload = incident(0, "INC-PHASE6-004")

    assert client.post("/assist", json=payload).status_code == 200
    assert client.post("/assist", json=payload).status_code == 409
    assert client.get("/recommendations/REC-MISSING", headers=AUDITOR_HEADERS).status_code == 404
    assert (
        client.get("/recommendations/REC-MISSING/audit", headers=AUDITOR_HEADERS).status_code == 404
    )


def test_rejection_requires_a_reason(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/assist", json=incident(0, "INC-PHASE6-005"))
    recommendation_id = created.json()["recommendation_id"]

    response = client.post(
        f"/recommendations/{recommendation_id}/reject",
        json={"reviewer": "service-desk-lead"},
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 422
