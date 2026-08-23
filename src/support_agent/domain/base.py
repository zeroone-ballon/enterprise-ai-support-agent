"""Shared configuration for strict domain models."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Reject unknown fields and normalize surrounding whitespace."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )
