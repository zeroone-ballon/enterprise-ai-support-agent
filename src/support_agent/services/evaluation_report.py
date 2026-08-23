"""Reproducible end-to-end evaluation against the fictional gold dataset."""

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from support_agent.adapters import JsonKnowledgeRepository
from support_agent.domain import Incident, RecommendationStatus
from support_agent.services.assist_service import AssistService
from support_agent.services.lexical_retriever import WeightedLexicalRetriever


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Aggregate safety and quality checks for one evaluation run."""

    cases_total: int
    cases_passed: int
    top1_accuracy: float
    abstention_accuracy: float
    grounding_accuracy: float
    freshness_accuracy: float
    high_risk_accuracy: float

    @property
    def passed(self) -> bool:
        return self.cases_passed == self.cases_total

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "passed": self.passed}


def evaluate(data_dir: Path) -> EvaluationReport:
    """Evaluate classification-independent recommendation safety outcomes."""

    incidents = [
        Incident.model_validate(item)
        for item in json.loads((data_dir / "incidents.json").read_text(encoding="utf-8"))
    ]
    gold_document = json.loads((data_dir / "gold_cases.json").read_text(encoding="utf-8"))
    cases = gold_document["cases"]
    repository = JsonKnowledgeRepository.from_path(data_dir / "knowledge.json")
    service = AssistService(
        repository,
        WeightedLexicalRetriever(repository),
        reference_date=date.fromisoformat(gold_document["freshness_reference_date"]),
    )

    top1 = abstention = grounding = freshness = high_risk = passed = 0
    for incident, gold in zip(incidents, cases, strict=True):
        result = service.assist(incident)
        actual_top = result.evidence[0].knowledge_id if result.evidence else None
        checks = (
            actual_top == gold["expected_top_knowledge_id"],
            (result.recommendation.status is RecommendationStatus.ABSTAINED)
            == gold["should_abstain"],
            result.evaluation.grounded == gold["expected_grounded"],
            result.evaluation.knowledge_fresh == gold["expected_knowledge_fresh"],
            result.evaluation.high_risk_action == gold["high_risk_action"],
        )
        top1 += checks[0]
        abstention += checks[1]
        grounding += checks[2]
        freshness += checks[3]
        high_risk += checks[4]
        passed += all(checks)

    total = len(cases)
    return EvaluationReport(
        cases_total=total,
        cases_passed=passed,
        top1_accuracy=top1 / total,
        abstention_accuracy=abstention / total,
        grounding_accuracy=grounding / total,
        freshness_accuracy=freshness / total,
        high_risk_accuracy=high_risk / total,
    )
