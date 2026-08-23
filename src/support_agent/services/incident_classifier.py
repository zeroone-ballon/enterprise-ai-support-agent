"""Deterministic incident classification for the Phase 5 workflow."""

from support_agent.domain import ClassificationSource, Incident, IncidentClassification, Priority
from support_agent.services.lexical_retriever import tokenize


class RuleBasedIncidentClassifier:
    """Preserve provided classifications and infer missing values from safe rules."""

    def classify(self, incident: Incident) -> IncidentClassification:
        """Return a complete category and priority for an incident."""

        if incident.category is not None and incident.priority is not None:
            return IncidentClassification(
                category=incident.category,
                priority=incident.priority,
                source=ClassificationSource.PROVIDED,
            )

        terms = tokenize(f"{incident.short_description} {incident.description}")
        category = incident.category or self._infer_category(terms)
        priority = incident.priority or self._infer_priority(category, terms)
        return IncidentClassification(
            category=category,
            priority=priority,
            source=ClassificationSource.INFERRED,
        )

    @staticmethod
    def _infer_category(terms: frozenset[str]) -> str:
        if terms & {"compromise", "security", "unfamiliar", "mfa"}:
            return "security"
        if terms & {"vpn", "remote", "network", "tunnel", "certificate"}:
            return "network"
        if "application" in terms:
            return "support"
        if terms & {"disk", "laptop", "printer", "device", "windows"}:
            return "hardware"
        if terms & {"account", "login", "password", "sign"}:
            return "access"
        return "support"

    @staticmethod
    def _infer_priority(category: str, terms: frozenset[str]) -> Priority:
        if category == "security" and terms & {"compromise", "unfamiliar", "attack"}:
            return Priority.P1
        if terms & {"critical", "outage", "widespread"}:
            return Priority.P2
        if category in {"access", "network"}:
            return Priority.P3
        return Priority.P4
