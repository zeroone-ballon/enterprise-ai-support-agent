"""Phase 10 evaluation, observability, and deployment-hardening tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent.config import Settings
from support_agent.main import create_app
from support_agent.services.evaluation_report import evaluate

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_gold_evaluation_report_passes() -> None:
    report = evaluate(DATA_DIR)

    assert report.passed is True
    assert report.cases_passed == report.cases_total == 8
    assert report.top1_accuracy == 1.0
    assert report.abstention_accuracy == 1.0
    assert report.grounding_accuracy == 1.0


def test_readiness_and_sanitized_metrics(tmp_path: Path) -> None:
    client = TestClient(
        create_app(Settings(app_env="test", lifecycle_db_path=tmp_path / "agent.db"))
    )

    ready = client.get("/ready", headers={"X-Request-ID": "trace-demo-001"})
    metrics = client.get("/metrics")

    assert ready.status_code == 200
    assert ready.headers["X-Request-ID"] == "trace-demo-001"
    assert ready.json() == {
        "status": "ready",
        "knowledge": "ready",
        "database": "ready",
    }
    assert metrics.json()["requests_total"] >= 1
    assert "trace-demo-001" not in metrics.text


def test_production_rejects_development_credentials() -> None:
    with pytest.raises(ValueError, match="development API-key digests"):
        create_app(Settings(app_env="production"))
