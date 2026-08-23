"""Tests for the Phase 1 application foundation."""

from fastapi.testclient import TestClient

from support_agent.config import Settings
from support_agent.main import create_app


def test_health_returns_public_service_metadata() -> None:
    settings = Settings(
        app_name="Enterprise AI Support Agent Test",
        app_env="test",
        app_version="0.1.0-test",
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Enterprise AI Support Agent Test",
        "version": "0.1.0-test",
        "environment": "test",
    }


def test_openapi_exposes_health_endpoint() -> None:
    client = TestClient(create_app(Settings(app_env="test")))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]

