"""Application health endpoint."""

from fastapi import APIRouter, Request

from support_agent.api.schemas.health import HealthResponse
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
