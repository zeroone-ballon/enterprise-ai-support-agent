"""Phase 2 tests for domain validation and cross-model invariants."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from support_agent.domain import (
    Approval,
    ApprovalStatus,
    AssistResponse,
    ClassificationSource,
    Evaluation,
    Evidence,
    Incident,
    IncidentClassification,
    KnowledgeArticle,
    KnowledgeStatus,
    Priority,
    Recommendation,
    RecommendationStatus,
)


def make_evidence() -> Evidence:
    return Evidence(
        knowledge_id="KB-DEMO-001",
        title="Unlocking a VPN account",
        score=0.86,
        matched_terms=["VPN", "locked", "vpn"],
        status=KnowledgeStatus.PUBLISHED,
        updated_at=date(2026, 7, 10),
    )


def make_classification() -> IncidentClassification:
    return IncidentClassification(
        category="access",
        priority=Priority.P3,
        source=ClassificationSource.INFERRED,
    )


def test_incident_trims_text_and_rejects_unknown_fields() -> None:
    incident = Incident(
        incident_id="INC-DEMO-001",
        short_description="  VPN account locked  ",
        description="  The user cannot connect.  ",
    )

    assert incident.short_description == "VPN account locked"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Incident(
            incident_id="INC-DEMO-001",
            short_description="VPN account locked",
            description="The user cannot connect.",
            caller_email="not-part-of-v0.1@example.invalid",
        )


def test_knowledge_normalizes_tags_and_rejects_duplicates() -> None:
    article = KnowledgeArticle(
        knowledge_id="KB-DEMO-001",
        title="Unlocking a VPN account",
        content="Verify identity, inspect lock state, unlock, and test the connection.",
        category="access",
        tags=["VPN", "Account", "Locked"],
        status=KnowledgeStatus.PUBLISHED,
        updated_at=date(2026, 7, 10),
    )

    assert article.tags == ["vpn", "account", "locked"]

    with pytest.raises(ValidationError, match="tags must be unique"):
        KnowledgeArticle(
            knowledge_id="KB-DEMO-002",
            title="Duplicate tags",
            content="Invalid demonstration article.",
            category="access",
            tags=["VPN", "vpn"],
            status=KnowledgeStatus.PUBLISHED,
            updated_at=date(2026, 7, 10),
        )


def test_evidence_enforces_score_range_and_deduplicates_terms() -> None:
    evidence = make_evidence()

    assert evidence.matched_terms == ["vpn", "locked"]

    with pytest.raises(ValidationError):
        Evidence(**{**evidence.model_dump(), "score": 1.1})


def test_recommendation_requires_response_and_abstention_forbids_it() -> None:
    with pytest.raises(ValidationError, match="requires suggested_response"):
        Recommendation(
            status=RecommendationStatus.RECOMMENDED,
            summary="VPN account may be locked.",
            suggested_response=None,
            next_actions=["Verify identity"],
        )

    with pytest.raises(ValidationError, match="must not include suggested_response"):
        Recommendation(
            status=RecommendationStatus.ABSTAINED,
            summary="Insufficient evidence.",
            suggested_response="Try resetting the account.",
            next_actions=["Escalate"],
        )


def test_rejected_approval_requires_reason() -> None:
    with pytest.raises(ValidationError, match="requires a reason"):
        Approval(
            status=ApprovalStatus.REJECTED,
            reviewer="demo-reviewer",
            decided_at=datetime(2026, 8, 23, tzinfo=UTC),
        )


def test_pending_approval_forbids_decision_metadata() -> None:
    with pytest.raises(ValidationError, match="must not contain decision metadata"):
        Approval(status=ApprovalStatus.PENDING, reviewer="too-early")


def test_decided_approval_requires_reviewer_and_timestamp() -> None:
    with pytest.raises(ValidationError, match="requires reviewer and decided_at"):
        Approval(status=ApprovalStatus.APPROVED)


def test_approval_is_always_required_in_v0_1() -> None:
    with pytest.raises(ValidationError, match="requires human approval"):
        Approval(required=False)


def test_execution_metadata_is_valid_only_for_executed_state() -> None:
    decision_time = datetime(2026, 8, 23, tzinfo=UTC)

    with pytest.raises(ValidationError, match="requires executed_at"):
        Approval(
            status=ApprovalStatus.EXECUTED,
            reviewer="demo-reviewer",
            decided_at=decision_time,
        )

    with pytest.raises(ValidationError, match="valid only for executed approval"):
        Approval(
            status=ApprovalStatus.APPROVED,
            reviewer="demo-reviewer",
            decided_at=decision_time,
            executed_at=decision_time,
        )

    executed = Approval(
        status=ApprovalStatus.EXECUTED,
        reviewer="demo-reviewer",
        decided_at=decision_time,
        executed_at=decision_time,
    )
    assert executed.status is ApprovalStatus.EXECUTED


def test_grounded_assist_response_requires_published_evidence() -> None:
    response = AssistResponse(
        recommendation_id="REC-DEMO-001",
        incident_id="INC-DEMO-001",
        classification=make_classification(),
        recommendation=Recommendation(
            status=RecommendationStatus.RECOMMENDED,
            summary="The VPN account may be locked.",
            suggested_response="Verify identity and inspect the account lock status.",
            next_actions=["Verify identity", "Check account lock status"],
        ),
        evidence=[make_evidence()],
        evaluation=Evaluation(
            grounded=True,
            knowledge_fresh=True,
            sufficient_context=True,
            high_risk_action=False,
        ),
        confidence=0.82,
        approval=Approval(),
    )

    assert response.approval.status is ApprovalStatus.PENDING
    assert response.model_dump(mode="json")["confidence"] == 0.82

    retired_evidence = make_evidence().model_copy(
        update={"status": KnowledgeStatus.RETIRED}
    )
    with pytest.raises(ValidationError, match="requires published evidence"):
        AssistResponse(
            **{
                **response.model_dump(),
                "evidence": [retired_evidence],
            }
        )


def test_recommended_response_must_be_evaluated_as_grounded() -> None:
    with pytest.raises(ValidationError, match="must be evaluated as grounded"):
        AssistResponse(
            recommendation_id="REC-DEMO-003",
            incident_id="INC-DEMO-003",
            classification=make_classification(),
            recommendation=Recommendation(
                status=RecommendationStatus.RECOMMENDED,
                summary="A recommendation with inconsistent evaluation.",
                suggested_response="This should be rejected by the aggregate model.",
                next_actions=["Reject inconsistent state"],
            ),
            evidence=[make_evidence()],
            evaluation=Evaluation(
                grounded=False,
                knowledge_fresh=True,
                sufficient_context=True,
                high_risk_action=False,
            ),
            confidence=0.8,
            approval=Approval(),
        )


def test_abstention_cannot_be_evaluated_as_grounded() -> None:
    with pytest.raises(ValidationError, match="cannot be evaluated as grounded"):
        AssistResponse(
            recommendation_id="REC-DEMO-004",
            incident_id="INC-DEMO-004",
            classification=make_classification(),
            recommendation=Recommendation(
                status=RecommendationStatus.ABSTAINED,
                summary="No published evidence.",
                suggested_response=None,
                next_actions=["Escalate"],
            ),
            evidence=[],
            evaluation=Evaluation(
                grounded=True,
                knowledge_fresh=False,
                sufficient_context=False,
                high_risk_action=False,
            ),
            confidence=0.0,
            approval=Approval(),
        )


def test_abstention_has_no_answer_evidence_or_confidence() -> None:
    response = AssistResponse(
        recommendation_id="REC-DEMO-099",
        incident_id="INC-DEMO-099",
        classification=make_classification(),
        recommendation=Recommendation(
            status=RecommendationStatus.ABSTAINED,
            summary="No sufficiently relevant published knowledge was found.",
            suggested_response=None,
            next_actions=["Collect diagnostic information", "Escalate"],
        ),
        evidence=[],
        evaluation=Evaluation(
            grounded=False,
            knowledge_fresh=False,
            sufficient_context=False,
            high_risk_action=False,
            violations=["INSUFFICIENT_EVIDENCE"],
        ),
        confidence=0.0,
        approval=Approval(),
    )

    assert response.recommendation.suggested_response is None
    assert response.confidence == 0.0

    with pytest.raises(ValidationError, match="zero confidence"):
        AssistResponse(**{**response.model_dump(), "confidence": 0.1})
