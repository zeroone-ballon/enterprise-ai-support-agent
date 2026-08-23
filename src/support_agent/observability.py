"""Dependency-free request logging and process-local service metrics."""

import json
import logging
import time
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

LOGGER = logging.getLogger("support_agent.requests")


class RequestMetrics:
    """Small in-process counters suitable for a single-process PoC."""

    def __init__(self) -> None:
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._failures = 0
        self._duration_ms_total = 0.0

    def record(self, method: str, route: str, status: int, duration_ms: float) -> None:
        self._requests[(method, route, status)] += 1
        self._failures += status >= 500
        self._duration_ms_total += duration_ms

    def snapshot(self) -> dict[str, object]:
        total = sum(self._requests.values())
        return {
            "requests_total": total,
            "failures_total": self._failures,
            "average_duration_ms": round(self._duration_ms_total / total, 3) if total else 0.0,
            "requests": [
                {"method": method, "route": route, "status": status, "count": count}
                for (method, route, status), count in sorted(self._requests.items())
            ],
        }


def configure_observability(application: FastAPI, log_level: str) -> None:
    """Install sanitized JSON access logging and correlation IDs."""

    resolved_level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(level=resolved_level)
    LOGGER.setLevel(resolved_level)
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    LOGGER.propagate = False
    metrics = RequestMetrics()
    application.state.request_metrics = metrics

    @application.middleware("http")
    async def observe_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        metrics.record(request.method, route_path, response.status_code, duration_ms)
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route_path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 3),
                },
                separators=(",", ":"),
            )
        )
        return response
