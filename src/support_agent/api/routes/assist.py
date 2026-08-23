"""Incident assistance endpoint."""

from fastapi import APIRouter, Request

from support_agent.domain import AssistResponse, Incident
from support_agent.services import AssistService

router = APIRouter(tags=["assistance"])


@router.post("/assist", response_model=AssistResponse)
def assist(incident: Incident, request: Request) -> AssistResponse:
    """Return a deterministic, evidence-backed, approval-gated recommendation."""

    service: AssistService = request.app.state.assist_service
    return service.assist(incident)
