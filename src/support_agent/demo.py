"""Live end-to-end release-candidate demonstration using only the standard library."""

import argparse
import json
import time
import urllib.error
import urllib.request
from typing import Any


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {error.code}: {detail}") from error


def run_demo(
    base_url: str,
    incident_id: str,
    reviewer_key: str,
    executor_key: str,
    auditor_key: str,
) -> dict[str, Any]:
    """Exercise approval, idempotency, audit, and side-effect boundaries."""

    created = _request(
        base_url,
        "POST",
        "/assist",
        payload={
            "incident_id": incident_id,
            "short_description": "VPN account locked after repeated sign-in attempts",
            "description": "The corporate VPN reports that the account is locked.",
            "category": "access",
            "priority": "P3",
        },
    )
    recommendation_id = created["recommendation_id"]
    approved = _request(
        base_url,
        "POST",
        f"/recommendations/{recommendation_id}/approve",
        payload={"reviewer": "service-desk-lead", "reason": "RC demo evidence verified"},
        headers={"X-API-Key": reviewer_key},
    )
    execution_headers = {
        "X-API-Key": executor_key,
        "Idempotency-Key": f"rc-demo-{incident_id}",
    }
    executed = _request(
        base_url,
        "POST",
        f"/recommendations/{recommendation_id}/execute",
        payload={"executor": "automation-operator"},
        headers=execution_headers,
    )
    replayed = _request(
        base_url,
        "POST",
        f"/recommendations/{recommendation_id}/execute",
        payload={"executor": "automation-operator"},
        headers=execution_headers,
    )
    audit = _request(
        base_url,
        "GET",
        f"/recommendations/{recommendation_id}/audit",
        headers={"X-API-Key": auditor_key},
    )
    summary = {
        "incident_id": incident_id,
        "recommendation_id": recommendation_id,
        "evidence_ids": [item["knowledge_id"] for item in created["evidence"]],
        "generation_mode": created["generation"]["mode"],
        "approval_status": approved["approval"]["status"],
        "execution_status": executed["receipt"]["status"],
        "side_effects": executed["receipt"]["side_effects"],
        "idempotent_replay": replayed == executed,
        "audit_events": [event["event_type"] for event in audit],
    }
    expected_events = [
        "recommendation_created",
        "recommendation_approved",
        "mock_execution_completed",
    ]
    if (
        summary["approval_status"] != "approved"
        or summary["execution_status"] != "simulated"
        or summary["side_effects"] is not False
        or summary["idempotent_replay"] is not True
        or summary["audit_events"] != expected_events
    ):
        raise RuntimeError("end-to-end release-candidate assertions failed")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 11 live end-to-end demo")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--incident-id", default=f"INC-RC-{time.time_ns()}")
    parser.add_argument("--reviewer-key", default="dev-reviewer-key")
    parser.add_argument("--executor-key", default="dev-executor-key")
    parser.add_argument("--auditor-key", default="dev-auditor-key")
    args = parser.parse_args()
    summary = run_demo(
        args.base_url,
        args.incident_id,
        args.reviewer_key,
        args.executor_key,
        args.auditor_key,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
