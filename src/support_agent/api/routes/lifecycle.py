"""Authenticated human decision, audit, and idempotent mock execution endpoints."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status

from support_agent.adapters import RecommendationNotFoundError
from support_agent.api.security import Principal, Role, authorize
from support_agent.domain import (
    ApprovalDecision,
    AssistResponse,
    AuditEvent,
    ExecutionRequest,
    ExecutionResult,
    RejectionDecision,
)
from support_agent.services import InvalidTransitionError, RecommendationLifecycleService

router = APIRouter(prefix="/recommendations", tags=["approval lifecycle"])


def _service(request: Request) -> RecommendationLifecycleService:
    return request.app.state.lifecycle_service


def _not_found(error: RecommendationNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="recommendation not found",
    )


def _conflict(error: InvalidTransitionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _principal(request: Request, *roles: Role) -> Principal:
    return authorize(request, frozenset(roles))


def _require_actor(principal: Principal, claimed_actor: str) -> None:
    if principal.actor != claimed_actor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="authenticated actor does not match request actor",
        )


@router.get("/{recommendation_id}", response_model=AssistResponse)
def get_recommendation(recommendation_id: str, request: Request) -> AssistResponse:
    _principal(request, Role.REVIEWER, Role.EXECUTOR, Role.AUDITOR)
    try:
        return _service(request).get(recommendation_id)
    except RecommendationNotFoundError as error:
        raise _not_found(error) from error


@router.post("/{recommendation_id}/approve", response_model=AssistResponse)
def approve(
    recommendation_id: str,
    decision: ApprovalDecision,
    request: Request,
) -> AssistResponse:
    principal = _principal(request, Role.REVIEWER)
    _require_actor(principal, decision.reviewer)
    try:
        return _service(request).approve(recommendation_id, decision)
    except RecommendationNotFoundError as error:
        raise _not_found(error) from error
    except InvalidTransitionError as error:
        raise _conflict(error) from error


@router.post("/{recommendation_id}/reject", response_model=AssistResponse)
def reject(
    recommendation_id: str,
    decision: RejectionDecision,
    request: Request,
) -> AssistResponse:
    principal = _principal(request, Role.REVIEWER)
    _require_actor(principal, decision.reviewer)
    try:
        return _service(request).reject(recommendation_id, decision)
    except RecommendationNotFoundError as error:
        raise _not_found(error) from error
    except InvalidTransitionError as error:
        raise _conflict(error) from error


@router.post("/{recommendation_id}/execute", response_model=ExecutionResult)
def execute(
    recommendation_id: str,
    execution_request: ExecutionRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
) -> ExecutionResult:
    principal = _principal(request, Role.EXECUTOR)
    _require_actor(principal, execution_request.executor)
    try:
        return _service(request).execute(
            recommendation_id,
            execution_request,
            idempotency_key=idempotency_key,
        )
    except RecommendationNotFoundError as error:
        raise _not_found(error) from error
    except InvalidTransitionError as error:
        raise _conflict(error) from error


@router.get("/{recommendation_id}/audit", response_model=list[AuditEvent])
def audit(recommendation_id: str, request: Request) -> list[AuditEvent]:
    _principal(request, Role.REVIEWER, Role.EXECUTOR, Role.AUDITOR)
    try:
        return _service(request).audit(recommendation_id)
    except RecommendationNotFoundError as error:
        raise _not_found(error) from error
