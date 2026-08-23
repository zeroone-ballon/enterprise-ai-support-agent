"""Deterministic, evidence-grounded assistance workflow."""

from datetime import date

from support_agent.domain import (
    Approval,
    AssistResponse,
    Evaluation,
    Evidence,
    Incident,
    Recommendation,
    RecommendationStatus,
)
from support_agent.domain.ports import KnowledgeRepository, Retriever
from support_agent.services.incident_classifier import RuleBasedIncidentClassifier
from support_agent.services.lexical_retriever import tokenize

TRIAGE_ARTICLE_IDS = frozenset({"KB-DEMO-007", "KB-DEMO-008"})
HIGH_RISK_TERMS = frozenset({"certificate", "compromise", "containment", "revoke", "unfamiliar"})
HIGH_RISK_ARTICLE_IDS = frozenset({"KB-DEMO-004", "KB-DEMO-009"})


class AssistService:
    """Classify, retrieve, evaluate, and produce an approval-gated response."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        retriever: Retriever,
        *,
        reference_date: date,
        freshness_max_age_days: int = 365,
    ) -> None:
        self._repository = repository
        self._retriever = retriever
        self._classifier = RuleBasedIncidentClassifier()
        self._reference_date = reference_date
        self._freshness_max_age_days = freshness_max_age_days

    def assist(self, incident: Incident) -> AssistResponse:
        """Build an auditable recommendation or explicit abstention."""

        classification = self._classifier.classify(incident)
        classified_incident = incident.model_copy(
            update={"category": classification.category, "priority": classification.priority}
        )
        evidence = self._retriever.search(classified_incident, limit=3)
        top_evidence = evidence[0] if evidence else None
        article = self._repository.get(top_evidence.knowledge_id) if top_evidence else None

        knowledge_fresh = bool(
            top_evidence
            and (self._reference_date - top_evidence.updated_at).days
            <= self._freshness_max_age_days
        )
        sufficient_context = bool(
            top_evidence and top_evidence.knowledge_id not in TRIAGE_ARTICLE_IDS
        )
        incident_terms = tokenize(f"{incident.short_description} {incident.description}")
        high_risk = bool(
            top_evidence
            and (
                top_evidence.knowledge_id in HIGH_RISK_ARTICLE_IDS
                or HIGH_RISK_TERMS & incident_terms
            )
        )
        can_recommend = bool(top_evidence and article and knowledge_fresh and sufficient_context)

        if can_recommend:
            recommendation = Recommendation(
                status=RecommendationStatus.RECOMMENDED,
                summary=f"Use {article.knowledge_id}: {article.title}",
                suggested_response=article.content,
                next_actions=[
                    "Review the cited evidence and proposed response.",
                    "Approve or reject the recommendation before any action is taken.",
                ],
            )
            confidence = top_evidence.score
        else:
            recommendation = self._abstention(top_evidence, knowledge_fresh, sufficient_context)
            confidence = 0.0

        return AssistResponse(
            recommendation_id=f"REC-{incident.incident_id}",
            incident_id=incident.incident_id,
            classification=classification,
            recommendation=recommendation,
            evidence=evidence,
            evaluation=Evaluation(
                grounded=can_recommend,
                knowledge_fresh=knowledge_fresh,
                sufficient_context=sufficient_context,
                high_risk_action=high_risk,
                violations=[],
            ),
            confidence=confidence,
            approval=Approval(),
        )

    @staticmethod
    def _abstention(
        top_evidence: Evidence | None,
        knowledge_fresh: bool,
        sufficient_context: bool,
    ) -> Recommendation:
        if top_evidence is None:
            summary = "No sufficiently relevant published knowledge was found."
            action = "Escalate to a human support specialist with the incident details."
        elif not sufficient_context:
            summary = "More diagnostic context is required before proposing a resolution."
            action = "Collect the missing details described in the cited triage article."
        elif not knowledge_fresh:
            summary = "The matching knowledge is stale and cannot safely ground a recommendation."
            action = "Request specialist review and an updated approved procedure."
        else:
            summary = "Policy prevents an automated recommendation."
            action = "Request human review."

        return Recommendation(
            status=RecommendationStatus.ABSTAINED,
            summary=summary,
            suggested_response=None,
            next_actions=[action],
        )
