"""Explicit, fail-closed ServiceNow PDI incident update adapter."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from support_agent.domain import (
    AssistResponse,
    ExecutionRequest,
    ServiceNowExecutionReceipt,
)


class ServiceNowPdiError(RuntimeError):
    """Raised when a PDI request cannot be proven safe and successful."""


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    body: bytes


class ServiceNowHttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse: ...


class UrllibServiceNowTransport:
    """Standard-library HTTPS transport with bounded response reads."""

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return HttpResponse(response.status, response.read(1_000_001))
        except (urllib.error.URLError, TimeoutError) as error:
            raise ServiceNowPdiError("ServiceNow PDI request failed") from error


class ServiceNowPdiExecutor:
    """Resolve one incident by number and update only its work notes."""

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

    def execute(
        self,
        response: AssistResponse,
        request: ExecutionRequest,
        executed_at: datetime,
    ) -> ServiceNowExecutionReceipt:
        number = response.incident_id
        sys_id = self._resolve_incident(number)
        evidence_ids = ", ".join(item.knowledge_id for item in response.evidence) or "none"
        recommendation = (
            response.recommendation.suggested_response or response.recommendation.summary
        )
        work_notes = (
            f"Approved AI support recommendation ({response.recommendation_id}).\n"
            f"Evidence: {evidence_ids}\n{recommendation}"
        )
        url = f"{self._base_url}/api/now/table/incident/{urllib.parse.quote(sys_id)}"
        result = self._json_request("PATCH", url, {"work_notes": work_notes})
        if not isinstance(result, dict) or result.get("number") != number:
            raise ServiceNowPdiError("ServiceNow PDI update response did not match the incident")
        return ServiceNowExecutionReceipt(
            recommendation_id=response.recommendation_id,
            executor=request.executor,
            executed_at=executed_at,
            target_number=number,
            target_sys_id=sys_id,
            summary=f"Updated work_notes on PDI incident {number}.",
        )

    def _resolve_incident(self, number: str) -> str:
        query = urllib.parse.urlencode(
            {
                "sysparm_query": f"number={number}",
                "sysparm_limit": "2",
                "sysparm_fields": "sys_id,number",
            }
        )
        result = self._json_request("GET", f"{self._base_url}/api/now/table/incident?{query}", None)
        if not isinstance(result, list) or len(result) != 1 or result[0].get("number") != number:
            raise ServiceNowPdiError("ServiceNow incident lookup must return exactly one match")
        sys_id = result[0].get("sys_id")
        if not isinstance(sys_id, str) or len(sys_id) != 32:
            raise ServiceNowPdiError("ServiceNow incident returned an invalid sys_id")
        return sys_id

    def _json_request(self, method: str, url: str, payload: dict[str, str] | None):
        headers = dict(self._headers)
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        response = self._transport.request(method, url, headers, body, self._timeout_seconds)
        if response.status < 200 or response.status >= 300 or len(response.body) > 1_000_000:
            raise ServiceNowPdiError("ServiceNow PDI returned an unsuccessful response")
        try:
            document = json.loads(response.body)
            return document["result"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise ServiceNowPdiError("ServiceNow PDI returned invalid JSON") from error
