"""Recommendation and quality evaluation models."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from support_agent.domain.base import DomainModel
from support_agent.domain.common import RecommendationStatus


class Recommendation(DomainModel):
    """Grounded support proposal or an explicit abstention."""

    status: RecommendationStatus
    summary: Annotated[str, Field(min_length=1, max_length=500)]
    suggested_response: Annotated[str, Field(min_length=1, max_length=4000)] | None = None
    next_actions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_response_for_status(self) -> Self:
        """A recommendation needs a response; an abstention must not fabricate one."""

        if self.status is RecommendationStatus.RECOMMENDED and self.suggested_response is None:
            raise ValueError("recommended status requires suggested_response")
        if self.status is RecommendationStatus.ABSTAINED and self.suggested_response is not None:
            raise ValueError("abstained status must not include suggested_response")
        return self


class Evaluation(DomainModel):
    """Policy and quality signals attached to every recommendation."""

    grounded: bool
    knowledge_fresh: bool
    sufficient_context: bool
    high_risk_action: bool
    violations: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
        max_length=50,
    )

