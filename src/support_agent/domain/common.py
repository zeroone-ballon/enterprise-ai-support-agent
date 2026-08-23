"""Enumerations shared across domain models."""

from enum import StrEnum


class Priority(StrEnum):
    """Support priority ordered from critical to low."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class KnowledgeStatus(StrEnum):
    """Lifecycle state of a knowledge article."""

    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class RecommendationStatus(StrEnum):
    """Whether the system can make a grounded recommendation."""

    RECOMMENDED = "recommended"
    ABSTAINED = "abstained"


class ApprovalStatus(StrEnum):
    """Allowed states in the approval and mock-execution workflow."""

    PENDING = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class ClassificationSource(StrEnum):
    """Origin of a category or priority classification."""

    PROVIDED = "provided"
    INFERRED = "inferred"

