"""Tests for isolated in-memory lifecycle persistence."""

from datetime import UTC, datetime

import pytest

from support_agent.adapters import (
    InMemoryLifecycleRepository,
    RecommendationNotFoundError,
)
from support_agent.domain import AuditEvent, AuditEventType


def test_unknown_recommendation_operations_fail() -> None:
    repository = InMemoryLifecycleRepository()

    with pytest.raises(RecommendationNotFoundError):
        repository.get("REC-MISSING")
    with pytest.raises(RecommendationNotFoundError):
        repository.list_events("REC-MISSING")


def test_audit_sequence_cannot_skip() -> None:
    repository = InMemoryLifecycleRepository()

    with pytest.raises(RecommendationNotFoundError):
        repository.append_event(
            AuditEvent(
                sequence=2,
                recommendation_id="REC-MISSING",
                event_type=AuditEventType.CREATED,
                actor="system",
                occurred_at=datetime.now(UTC),
            )
        )
