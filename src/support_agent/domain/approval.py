"""Human approval state with enforceable decision metadata."""

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, model_validator

from support_agent.domain.base import DomainModel
from support_agent.domain.common import ApprovalStatus


class Approval(DomainModel):
    """Approval information for a recommendation and mock execution."""

    required: bool = True
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    reason: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    decided_at: datetime | None = None
    executed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_state_metadata(self) -> Self:
        """Reject approval states that are missing required audit metadata."""

        if not self.required:
            raise ValueError("v0.1 requires human approval for every recommendation")

        if self.status is ApprovalStatus.PENDING:
            if any((self.reviewer, self.reason, self.decided_at, self.executed_at)):
                raise ValueError("pending approval must not contain decision metadata")
            return self

        if self.reviewer is None or self.decided_at is None:
            raise ValueError("decided approval requires reviewer and decided_at")

        if self.status is ApprovalStatus.REJECTED and self.reason is None:
            raise ValueError("rejected approval requires a reason")

        if self.status is ApprovalStatus.EXECUTED and self.executed_at is None:
            raise ValueError("executed approval requires executed_at")

        if self.status is not ApprovalStatus.EXECUTED and self.executed_at is not None:
            raise ValueError("executed_at is valid only for executed approval")

        return self

