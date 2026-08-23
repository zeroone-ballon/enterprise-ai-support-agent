"""ServiceNow-compatible sandbox action contract."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from support_agent.domain.base import DomainModel
from support_agent.domain.response import RecommendationId


class ServiceNowSandboxAction(DomainModel):
    """Validated outbound shape recorded locally without making an HTTP request."""

    action_id: Annotated[str, Field(min_length=1, max_length=96)]
    recommendation_id: RecommendationId
    target_table: Literal["incident"] = "incident"
    target_correlation_id: Annotated[str, Field(min_length=1, max_length=64)]
    operation: Literal["update"] = "update"
    fields: dict[str, Annotated[str, Field(min_length=1, max_length=4000)]]
    mode: Literal["sandbox"] = "sandbox"
    created_at: datetime
