"""Metrics for deterministic retriever evaluation against Phase 3 gold data."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from support_agent.domain.incident import Incident
from support_agent.domain.ports import Retriever


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    """Portfolio-friendly metrics derived from gold retrieval expectations."""

    top1_correct: int
    top1_total: int
    relevant_retrieved: int
    relevant_total: int
    no_match_correct: int
    no_match_total: int

    @property
    def top1_accuracy(self) -> float:
        return self.top1_correct / self.top1_total if self.top1_total else 1.0

    @property
    def top3_recall(self) -> float:
        return self.relevant_retrieved / self.relevant_total if self.relevant_total else 1.0

    @property
    def no_match_accuracy(self) -> float:
        return self.no_match_correct / self.no_match_total if self.no_match_total else 1.0


def evaluate_retriever(
    retriever: Retriever,
    incidents: Iterable[Incident],
    gold_cases: Iterable[dict[str, Any]],
) -> RetrievalMetrics:
    """Evaluate Top-1, Top-3 recall, and deliberate no-match behavior."""

    incidents_by_id = {incident.incident_id: incident for incident in incidents}
    top1_correct = 0
    top1_total = 0
    relevant_retrieved = 0
    relevant_total = 0
    no_match_correct = 0
    no_match_total = 0

    for case in gold_cases:
        incident = incidents_by_id[case["incident_id"]]
        evidence = retriever.search(incident, limit=3)
        retrieved_ids = [item.knowledge_id for item in evidence]
        expected_top = case["expected_top_knowledge_id"]
        relevant_ids = set(case["relevant_knowledge_ids"])

        if expected_top is not None:
            top1_total += 1
            top1_correct += bool(retrieved_ids and retrieved_ids[0] == expected_top)

        relevant_total += len(relevant_ids)
        relevant_retrieved += len(relevant_ids & set(retrieved_ids))

        if not relevant_ids:
            no_match_total += 1
            no_match_correct += not retrieved_ids

    return RetrievalMetrics(
        top1_correct=top1_correct,
        top1_total=top1_total,
        relevant_retrieved=relevant_retrieved,
        relevant_total=relevant_total,
        no_match_correct=no_match_correct,
        no_match_total=no_match_total,
    )
