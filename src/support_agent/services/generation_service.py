"""Structured generation, grounding guardrails, and deterministic fallback."""

from dataclasses import dataclass

from support_agent.domain import (
    Evidence,
    GeneratedDraft,
    GenerationMetadata,
    Incident,
    KnowledgeArticle,
)
from support_agent.domain.ports import RecommendationGenerationPort
from support_agent.services.lexical_retriever import tokenize

UNSAFE_INSTRUCTIONS = (
    "bypass identity verification",
    "disable mfa immediately",
    "delete system files",
    "share the recovery key",
    "turn off endpoint protection",
)


class DeterministicRecommendationGenerator:
    """Produce the established Phase 5 response directly from approved knowledge."""

    provider_name = "deterministic"

    def generate(
        self,
        incident: Incident,
        article: KnowledgeArticle,
        evidence: list[Evidence],
    ) -> GeneratedDraft:
        del incident
        return GeneratedDraft(
            summary=f"Use {article.knowledge_id}: {article.title}",
            suggested_response=article.content,
            next_actions=[
                "Review the cited evidence and proposed response.",
                "Approve or reject the recommendation before any action is taken.",
            ],
            cited_knowledge_ids=[item.knowledge_id for item in evidence],
        )


class GenerationGuardrail:
    """Reject ungrounded citations and explicitly unsafe generated instructions."""

    def violations(
        self,
        draft: GeneratedDraft,
        article: KnowledgeArticle,
        evidence: list[Evidence],
    ) -> list[str]:
        evidence_ids = {item.knowledge_id for item in evidence}
        cited_ids = set(draft.cited_knowledge_ids)
        violations: list[str] = []
        if evidence and evidence[0].knowledge_id not in cited_ids:
            violations.append("top evidence was not cited")
        unknown = sorted(cited_ids - evidence_ids)
        if unknown:
            violations.append(f"unknown evidence citations: {','.join(unknown)}")
        grounded_terms = tokenize(draft.suggested_response) & tokenize(article.content)
        if len(grounded_terms) < 3:
            violations.append("generated response has insufficient lexical grounding")
        normalized_response = draft.suggested_response.casefold()
        for instruction in UNSAFE_INSTRUCTIONS:
            if instruction in normalized_response:
                violations.append(f"unsafe instruction: {instruction}")
        return violations


@dataclass(frozen=True, slots=True)
class GenerationOutcome:
    draft: GeneratedDraft
    metadata: GenerationMetadata


class GenerationCoordinator:
    """Use an optional provider only when its validated output passes guardrails."""

    def __init__(
        self,
        primary: RecommendationGenerationPort | None = None,
        *,
        fallback: RecommendationGenerationPort | None = None,
        guardrail: GenerationGuardrail | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback or DeterministicRecommendationGenerator()
        self._guardrail = guardrail or GenerationGuardrail()

    def generate(
        self,
        incident: Incident,
        article: KnowledgeArticle,
        evidence: list[Evidence],
        *,
        allow_primary: bool = True,
    ) -> GenerationOutcome:
        if self._primary is None:
            draft = self._fallback.generate(incident, article, evidence)
            return GenerationOutcome(draft=draft, metadata=GenerationMetadata())

        if not allow_primary:
            fallback_draft = self._fallback.generate(incident, article, evidence)
            return GenerationOutcome(
                draft=fallback_draft,
                metadata=GenerationMetadata(
                    provider=self._fallback.provider_name,
                    fallback_used=True,
                    violations=["LLM generation disabled for high-risk incident"],
                ),
            )

        violations: list[str] = []
        try:
            draft = self._primary.generate(incident, article, evidence)
            violations = self._guardrail.violations(draft, article, evidence)
            if not violations:
                return GenerationOutcome(
                    draft=draft,
                    metadata=GenerationMetadata(
                        mode="llm",
                        provider=self._primary.provider_name,
                    ),
                )
        except Exception as error:  # Provider and validation failures must fail closed.
            violations = [f"provider failure: {type(error).__name__}"]

        fallback_draft = self._fallback.generate(incident, article, evidence)
        return GenerationOutcome(
            draft=fallback_draft,
            metadata=GenerationMetadata(
                provider=self._fallback.provider_name,
                fallback_used=True,
                violations=violations,
            ),
        )
