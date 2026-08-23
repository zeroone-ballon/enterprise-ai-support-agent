"""Incident assistance endpoint."""

from fastapi import APIRouter, HTTPException, Request, status

from support_agent.adapters import DuplicateRecommendationError
from support_agent.domain import AssistResponse, Incident
from support_agent.services import RecommendationLifecycleService

router = APIRouter(tags=["assistance"])


@router.post("/assist", response_model=AssistResponse)
def assist(incident: Incident, request: Request) -> AssistResponse:
    """Return a deterministic, evidence-backed, approval-gated recommendation."""

    service: RecommendationLifecycleService = request.app.state.lifecycle_service
    try:
        return service.create(incident)
    except DuplicateRecommendationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="recommendation_id already exists",
        ) from error
