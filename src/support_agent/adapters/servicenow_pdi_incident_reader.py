"""Read and translate one ServiceNow PDI incident into the domain model."""

import base64
import json
import urllib.parse
from typing import Any

from pydantic import TypeAdapter, ValidationError

from support_agent.adapters.servicenow_pdi_executor import (
    ServiceNowHttpTransport,
    UrllibServiceNowTransport,
)
from support_agent.domain import Incident, Priority
from support_agent.domain.incident import IncidentId

INCIDENT_ID_ADAPTER = TypeAdapter(IncidentId)


class ServiceNowIncidentReadError(RuntimeError):
    """Raised when a PDI incident cannot be read and validated safely."""


class ServiceNowPdiIncidentReader:
    """Resolve an exact incident number and map approved fields to ``Incident``."""

    _PRIORITIES = {
        "1": Priority.P1,
        "2": Priority.P2,
        "3": Priority.P3,
        "4": Priority.P4,
        "5": Priority.P4,
    }

    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        *,
        timeout_seconds: float = 10.0,
        transport: ServiceNowHttpTransport | None = None,
    ) -> None:
        parsed = urllib.parse.urlsplit(instance_url)
        hostname = parsed.hostname or ""
        if (
            parsed.scheme != "https"
            or not hostname.endswith(".service-now.com")
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or parsed.username
        ):
            raise ValueError("ServiceNow instance URL must be an HTTPS service-now.com origin")
        if not username or not password:
            raise ValueError("ServiceNow PDI credentials are required")
        self._base_url = instance_url.rstrip("/")
        token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        self._headers = {"Accept": "application/json", "Authorization": f"Basic {token}"}
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibServiceNowTransport()

    def get(self, incident_id: str) -> Incident:
        """Return exactly one validated incident without exposing ServiceNow fields upstream."""

        try:
            validated_number = INCIDENT_ID_ADAPTER.validate_python(incident_id)
        except ValidationError as error:
            raise ServiceNowIncidentReadError("Invalid ServiceNow incident number") from error

        query = urllib.parse.urlencode(
            {
                "sysparm_query": f"number={validated_number}",
                "sysparm_limit": "2",
                "sysparm_fields": ("sys_id,number,short_description,description,category,priority"),
            }
        )
        url = f"{self._base_url}/api/now/table/incident?{query}"
        response = self._transport.request(
            "GET", url, dict(self._headers), None, self._timeout_seconds
        )
        if response.status < 200 or response.status >= 300 or len(response.body) > 1_000_000:
            raise ServiceNowIncidentReadError("ServiceNow PDI returned an unsuccessful response")
        try:
            result = json.loads(response.body)["result"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise ServiceNowIncidentReadError("ServiceNow PDI returned invalid JSON") from error
        if (
            not isinstance(result, list)
            or len(result) != 1
            or not isinstance(result[0], dict)
            or result[0].get("number") != validated_number
        ):
            raise ServiceNowIncidentReadError(
                "ServiceNow incident lookup must return exactly one match"
            )
        return self._to_incident(result[0])

    def _to_incident(self, record: dict[str, Any]) -> Incident:
        short_description = record.get("short_description")
        description = record.get("description") or short_description
        category = record.get("category") or None
        priority = self._PRIORITIES.get(str(record.get("priority", "")))
        try:
            return Incident(
                incident_id=record.get("number"),
                short_description=short_description,
                description=description,
                category=category,
                priority=priority,
            )
        except ValidationError as error:
            raise ServiceNowIncidentReadError(
                "ServiceNow incident fields failed domain validation"
            ) from error
