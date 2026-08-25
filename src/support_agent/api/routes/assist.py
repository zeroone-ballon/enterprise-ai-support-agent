"""Incident assistance endpoint."""

from fastapi import APIRouter, HTTPException, Request, status

from support_agent.adapters import DuplicateRecommendationError, ServiceNowIncidentReadError
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


@router.post("/assist/servicenow/{incident_number}", response_model=AssistResponse)
def assist_from_servicenow(incident_number: str, request: Request) -> AssistResponse:
    """Read one PDI incident and create the normal approval-gated recommendation."""

    reader = request.app.state.servicenow_incident_reader
    if reader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ServiceNow incident reading is not configured",
        )
    try:
        incident = reader.get(incident_number)
        service: RecommendationLifecycleService = request.app.state.lifecycle_service
        return service.create(incident)
    except ServiceNowIncidentReadError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except DuplicateRecommendationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="recommendation_id already exists",
        ) from error
