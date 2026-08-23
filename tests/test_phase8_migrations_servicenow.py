"""Phase 8 migration, credential, and ServiceNow sandbox contract tests."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from support_agent.adapters import ServiceNowSandboxExecutor, SqliteLifecycleRepository
from support_agent.config import Settings
from support_agent.domain import AssistResponse
from support_agent.main import create_app

REVIEWER = {"X-API-Key": "dev-reviewer-key"}
EXECUTOR = {"X-API-Key": "dev-executor-key", "Idempotency-Key": "phase8-contract-key"}


def demo_incident() -> dict[str, str]:
    return {
        "incident_id": "INC-PHASE8-001",
        "short_description": "VPN account locked after repeated sign-in attempts",
        "description": "The corporate VPN reports that the account is locked.",
        "category": "access",
        "priority": "P3",
    }


def test_existing_phase7_database_is_migrated_without_data_loss(tmp_path: Path) -> None:
    database = tmp_path / "upgrade.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE recommendations (
                recommendation_id TEXT PRIMARY KEY,
                response_json TEXT NOT NULL
            );
            CREATE TABLE audit_events (
                recommendation_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_json TEXT NOT NULL,
                PRIMARY KEY (recommendation_id, sequence)
            );
            CREATE TABLE execution_results (
                recommendation_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                result_json TEXT NOT NULL,
                PRIMARY KEY (recommendation_id, idempotency_key)
            );
            INSERT INTO recommendations VALUES ('legacy-record', '{}');
            """
        )

    SqliteLifecycleRepository(database)
    SqliteLifecycleRepository(database)

    with sqlite3.connect(database) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        legacy_count = connection.execute(
            "SELECT COUNT(*) FROM recommendations WHERE recommendation_id = 'legacy-record'"
        ).fetchone()[0]
        sandbox_table = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='servicenow_sandbox_actions'"
        ).fetchone()[0]

    assert versions == [(1,), (2,), (3,)]
    assert legacy_count == 1
    assert sandbox_table == 1


def test_servicenow_sandbox_contract_is_recorded_without_external_side_effects(
    tmp_path: Path,
) -> None:
    database = tmp_path / "sandbox.db"
    client = TestClient(create_app(Settings(lifecycle_db_path=database)))
    created = client.post("/assist", json=demo_incident()).json()
    recommendation_id = created["recommendation_id"]
    client.post(
        f"/recommendations/{recommendation_id}/approve",
        headers=REVIEWER,
        json={"reviewer": "service-desk-lead", "reason": "contract verified"},
    )
    executed = client.post(
        f"/recommendations/{recommendation_id}/execute",
        headers=EXECUTOR,
        json={"executor": "automation-operator"},
    )

    assert executed.status_code == 200
    assert executed.json()["receipt"]["side_effects"] is False
    assert "no HTTP call was made" in executed.json()["receipt"]["summary"]

    actions = ServiceNowSandboxExecutor(database).list_actions()
    assert len(actions) == 1
    action = actions[0]
    assert action.target_table == "incident"
    assert action.target_correlation_id == "INC-PHASE8-001"
    assert action.operation == "update"
    assert action.mode == "sandbox"
    assert action.fields["u_ai_execution_mode"] == "sandbox"
    assert action.fields["u_ai_recommendation_id"] == recommendation_id
    assert "KB-DEMO-001" in action.fields["u_ai_evidence_ids"]


def test_sandbox_action_builder_matches_contract_fixture(tmp_path: Path) -> None:
    fixture = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "incidents.json").read_text(
            encoding="utf-8"
        )
    )[0]
    client = TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "builder.db")))
    response = AssistResponse.model_validate(client.post("/assist", json=fixture).json())

    action = ServiceNowSandboxExecutor.build_action(
        response,
        datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
    )

    assert action.action_id == "SN-SBX-REC-INC-DEMO-001"
    assert set(action.fields) == {
        "work_notes",
        "u_ai_recommendation_id",
        "u_ai_evidence_ids",
        "u_ai_execution_mode",
    }


def test_settings_store_only_api_key_hashes() -> None:
    settings = Settings()

    assert not hasattr(settings, "reviewer_api_key")
    assert len(settings.reviewer_api_key_sha256) == 64
    assert "dev-reviewer-key" not in repr(settings)
