"""Health API schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Public liveness response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Dependency readiness response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"]
    knowledge: Literal["ready"]
    database: Literal["ready"]
