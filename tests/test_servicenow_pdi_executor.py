"""Opt-in ServiceNow PDI adapter contract tests without network access."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent.adapters.servicenow_pdi_executor import (
    HttpResponse,
    ServiceNowPdiError,
    ServiceNowPdiExecutor,
)
from support_agent.config import Settings
from support_agent.domain import AssistResponse, ExecutionRequest
from support_agent.main import create_app


class FakeTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = iter(responses)
        self.requests: list[tuple[str, str, dict[str, str], bytes | None]] = []

    def request(self, method, url, headers, body, timeout_seconds):
        self.requests.append((method, url, headers, body))
        return next(self.responses)


def response(tmp_path: Path) -> AssistResponse:
    client = TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "pdi-source.db")))
    return AssistResponse.model_validate(
        client.post(
            "/assist",
            json={
                "incident_id": "INC0012345",
                "short_description": "VPN account locked after repeated sign-in attempts",
                "description": "The corporate VPN reports that the account is locked.",
                "category": "access",
                "priority": "P3",
            },
        ).json()
    )


def test_pdi_executor_updates_only_work_notes(tmp_path: Path) -> None:
    sys_id = "a" * 32
    transport = FakeTransport(
        [
            HttpResponse(
                200, json.dumps({"result": [{"sys_id": sys_id, "number": "INC0012345"}]}).encode()
            ),
            HttpResponse(
                200, json.dumps({"result": {"sys_id": sys_id, "number": "INC0012345"}}).encode()
            ),
        ]
    )
    executor = ServiceNowPdiExecutor(
        "https://dev12345.service-now.com",
        "integration-user",
        "secret",
        transport=transport,
    )

    receipt = executor.execute(
        response(tmp_path),
        ExecutionRequest(executor="automation-operator"),
        datetime(2026, 8, 23, tzinfo=UTC),
    )

    assert receipt.status == "completed"
    assert receipt.side_effects is True
    assert receipt.target_number == "INC0012345"
    assert [item[0] for item in transport.requests] == ["GET", "PATCH"]
    patch_document = json.loads(transport.requests[1][3])
    assert set(patch_document) == {"work_notes"}
    assert "KB-DEMO-001" in patch_document["work_notes"]
    assert "secret" not in repr(executor)


def test_pdi_executor_fails_closed_for_ambiguous_lookup(tmp_path: Path) -> None:
    transport = FakeTransport([HttpResponse(200, b'{"result":[]}')])
    executor = ServiceNowPdiExecutor(
        "https://dev12345.service-now.com", "user", "secret", transport=transport
    )

    with pytest.raises(ServiceNowPdiError, match="exactly one"):
        executor.execute(
            response(tmp_path),
            ExecutionRequest(executor="automation-operator"),
            datetime(2026, 8, 23, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://dev12345.service-now.com",
        "https://example.com",
        "https://dev12345.service-now.com/unexpected",
    ],
)
def test_pdi_executor_rejects_unsafe_instance_url(url: str) -> None:
    with pytest.raises(ValueError, match="HTTPS service-now.com origin"):
        ServiceNowPdiExecutor(url, "user", "secret")
