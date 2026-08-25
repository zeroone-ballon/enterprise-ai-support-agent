"""ServiceNow PDI incident intake tests without network access."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent.adapters.servicenow_pdi_executor import HttpResponse
from support_agent.adapters.servicenow_pdi_incident_reader import (
    ServiceNowIncidentReadError,
    ServiceNowPdiIncidentReader,
)
from support_agent.config import Settings
from support_agent.domain import Priority
from support_agent.main import create_app


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.requests = []

    def request(self, method, url, headers, body, timeout_seconds):
        self.requests.append((method, url, headers, body, timeout_seconds))
        return self.response


def record(**overrides):
    value = {
        "sys_id": "a" * 32,
        "number": "INC0012345",
        "short_description": "VPN account locked",
        "description": "The VPN reports that the corporate account is locked.",
        "category": "access",
        "priority": "3",
    }
    value.update(overrides)
    return value


def reader_for(result) -> tuple[ServiceNowPdiIncidentReader, FakeTransport]:
    transport = FakeTransport(HttpResponse(200, json.dumps({"result": result}).encode()))
    reader = ServiceNowPdiIncidentReader(
        "https://dev12345.service-now.com", "integration-user", "secret", transport=transport
    )
    return reader, transport


def test_reader_maps_only_domain_incident_fields() -> None:
    reader, transport = reader_for([record()])

    incident = reader.get("INC0012345")

    assert incident.incident_id == "INC0012345"
    assert incident.category == "access"
    assert incident.priority is Priority.P3
    assert transport.requests[0][0] == "GET"
    assert "sysparm_limit=2" in transport.requests[0][1]
    assert "secret" not in repr(reader)


def test_reader_uses_short_description_when_description_is_empty() -> None:
    reader, _ = reader_for([record(description="")])

    incident = reader.get("INC0012345")

    assert incident.description == "VPN account locked"


@pytest.mark.parametrize("result", [[], [record(), record()]])
def test_reader_fails_closed_for_non_unique_result(result) -> None:
    reader, _ = reader_for(result)

    with pytest.raises(ServiceNowIncidentReadError, match="exactly one"):
        reader.get("INC0012345")


def test_reader_rejects_invalid_service_now_record() -> None:
    reader, _ = reader_for([record(short_description="", description="")])

    with pytest.raises(ServiceNowIncidentReadError, match="domain validation"):
        reader.get("INC0012345")


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (HttpResponse(500, b"{}"), "unsuccessful"),
        (HttpResponse(200, b"not-json"), "invalid JSON"),
    ],
)
def test_reader_fails_closed_for_bad_pdi_response(response, message) -> None:
    transport = FakeTransport(response)
    reader = ServiceNowPdiIncidentReader(
        "https://dev12345.service-now.com", "user", "secret", transport=transport
    )

    with pytest.raises(ServiceNowIncidentReadError, match=message):
        reader.get("INC0012345")


def test_reader_rejects_invalid_incident_number_before_network() -> None:
    reader, transport = reader_for([record()])

    with pytest.raises(ServiceNowIncidentReadError, match="Invalid"):
        reader.get("INC 0012345")

    assert transport.requests == []


def test_api_is_disabled_without_pdi_credentials(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(lifecycle_db_path=tmp_path / "disabled.db")))

    response = client.post("/assist/servicenow/INC0012345")

    assert response.status_code == 503


def test_api_creates_recommendation_from_pdi_incident(tmp_path: Path) -> None:
    app = create_app(Settings(lifecycle_db_path=tmp_path / "reader.db"))
    reader, _ = reader_for([record()])
    app.state.servicenow_incident_reader = reader
    client = TestClient(app)

    response = client.post("/assist/servicenow/INC0012345")

    assert response.status_code == 200
    assert response.json()["incident_id"] == "INC0012345"
    assert response.json()["approval"]["status"] == "pending_approval"


def test_api_maps_pdi_read_failure_to_bad_gateway(tmp_path: Path) -> None:
    app = create_app(Settings(lifecycle_db_path=tmp_path / "failure.db"))
    reader, _ = reader_for([])
    app.state.servicenow_incident_reader = reader
    client = TestClient(app)

    response = client.post("/assist/servicenow/INC0012345")

    assert response.status_code == 502
