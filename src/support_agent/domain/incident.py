"""Incident intake and classification models."""

from typing import Annotated

from pydantic import Field

from support_agent.domain.base import DomainModel
from support_agent.domain.common import ClassificationSource, Priority

IncidentId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")]
Category = Annotated[str, Field(min_length=1, max_length=80)]


class Incident(DomainModel):
    """Validated incident submitted to the support workflow."""

    incident_id: IncidentId
    short_description: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(min_length=1, max_length=4000)]
    category: Category | None = None
    priority: Priority | None = None


class IncidentClassification(DomainModel):
    """Category and priority selected for workflow processing."""

    category: Category
    priority: Priority
    source: ClassificationSource
