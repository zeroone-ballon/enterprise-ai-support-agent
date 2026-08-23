"""HTTP contract tests for POST /assist."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent.config import Settings
from support_agent.main import create_app

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "assist.db")))


def test_assist_endpoint_returns_auditable_response(client: TestClient) -> None:
    incident = json.loads((DATA_DIR / "incidents.json").read_text(encoding="utf-8"))[0]

    response = client.post("/assist", json=incident)

    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_id"] == "REC-INC-DEMO-001"
    assert body["evidence"][0]["knowledge_id"] == "KB-DEMO-001"
    assert body["recommendation"]["status"] == "recommended"
    assert body["approval"]["status"] == "pending_approval"


def test_assist_endpoint_rejects_invalid_incident(client: TestClient) -> None:
    response = client.post(
        "/assist",
        json={"incident_id": "bad id", "short_description": "", "description": ""},
    )

    assert response.status_code == 422


def test_openapi_documents_assist_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    operation = schema["paths"]["/assist"]["post"]
    assert operation["tags"] == ["assistance"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
