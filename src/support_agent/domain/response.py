"""Aggregate response returned by the future assist workflow."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from support_agent.domain.approval import Approval
from support_agent.domain.base import DomainModel
from support_agent.domain.common import KnowledgeStatus, RecommendationStatus
from support_agent.domain.incident import IncidentClassification, IncidentId
from support_agent.domain.knowledge import Evidence
from support_agent.domain.recommendation import Evaluation, Recommendation

RecommendationId = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$"),
]


class AssistResponse(DomainModel):
    """Auditable output assembled for an incident assistance request."""

    recommendation_id: RecommendationId
    incident_id: IncidentId
    classification: IncidentClassification
    recommendation: Recommendation
    evidence: list[Evidence] = Field(default_factory=list, max_length=3)
    evaluation: Evaluation
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    approval: Approval

    @model_validator(mode="after")
    def validate_grounding_contract(self) -> Self:
        """Keep recommendation, evidence, evaluation, and confidence consistent."""

        has_published_evidence = any(
            item.status is KnowledgeStatus.PUBLISHED for item in self.evidence
        )

        if self.recommendation.status is RecommendationStatus.RECOMMENDED:
            if not has_published_evidence:
                raise ValueError("recommended response requires published evidence")
            if not self.evaluation.grounded:
                raise ValueError("recommended response must be evaluated as grounded")

        if self.recommendation.status is RecommendationStatus.ABSTAINED:
            if self.evaluation.grounded:
                raise ValueError("abstained response cannot be evaluated as grounded")
            if self.confidence != 0.0:
                raise ValueError("abstained response must have zero confidence")

        return self
