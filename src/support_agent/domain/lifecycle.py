"""Approval lifecycle, audit, and simulated execution models."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from support_agent.domain.base import DomainModel
from support_agent.domain.response import AssistResponse, RecommendationId

Actor = Annotated[str, Field(min_length=1, max_length=120)]
DecisionReason = Annotated[str, Field(min_length=1, max_length=1000)]


class AuditEventType(StrEnum):
    """Events retained in order for each recommendation."""

    CREATED = "recommendation_created"
    APPROVED = "recommendation_approved"
    REJECTED = "recommendation_rejected"
    EXECUTED = "mock_execution_completed"
    PDI_UPDATED = "servicenow_pdi_update_completed"


class ApprovalDecision(DomainModel):
    """Human approval input."""

    reviewer: Actor
    reason: DecisionReason | None = None


class RejectionDecision(DomainModel):
    """Human rejection input requiring an auditable reason."""

    reviewer: Actor
    reason: DecisionReason


class ExecutionRequest(DomainModel):
    """Actor requesting a simulated execution."""

    executor: Actor


class AuditEvent(DomainModel):
    """Immutable event appended to a recommendation's history."""

    sequence: Annotated[int, Field(ge=1)]
    recommendation_id: RecommendationId
    event_type: AuditEventType
    actor: Actor
    occurred_at: datetime
    details: dict[str, str] = Field(default_factory=dict)


class MockExecutionReceipt(DomainModel):
    """Proof that only the isolated mock executor was invoked."""

    recommendation_id: RecommendationId
    status: Literal["simulated"] = "simulated"
    executor: Actor
    executed_at: datetime
    side_effects: Literal[False] = False
    summary: str = "No external system was changed."


class ServiceNowExecutionReceipt(DomainModel):
    """Proof of an approved update to one PDI incident."""

    recommendation_id: RecommendationId
    status: Literal["completed"] = "completed"
    executor: Actor
    executed_at: datetime
    side_effects: Literal[True] = True
    target_table: Literal["incident"] = "incident"
    target_number: str
    target_sys_id: str
    summary: str


class ExecutionResult(DomainModel):
    """Updated recommendation plus its execution receipt."""

    recommendation: AssistResponse
    receipt: MockExecutionReceipt | ServiceNowExecutionReceipt
