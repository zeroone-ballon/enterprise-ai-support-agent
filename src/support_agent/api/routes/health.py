"""Application health endpoint."""

from fastapi import APIRouter, Request

from support_agent.api.schemas.health import HealthResponse, ReadinessResponse
from support_agent.config import Settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Check service health")
def get_health(request: Request) -> HealthResponse:
    """Return liveness and public service metadata."""

    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Check service readiness")
def get_readiness(request: Request) -> ReadinessResponse:
    """Confirm that configured local dependencies can be opened."""

    settings: Settings = request.app.state.settings
    settings.knowledge_path.open("rb").close()
    settings.lifecycle_db_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.lifecycle_db_path.open("ab"):
        pass
    return ReadinessResponse(status="ready", knowledge="ready", database="ready")


@router.get("/metrics", summary="Inspect sanitized process metrics")
def get_metrics(request: Request) -> dict[str, object]:
    """Return process-local HTTP counters without request bodies or credentials."""

    return request.app.state.request_metrics.snapshot()
