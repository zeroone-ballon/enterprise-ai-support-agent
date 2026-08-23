"""Tests for deterministic incident classification."""

from support_agent.domain import ClassificationSource, Incident, Priority
from support_agent.services import RuleBasedIncidentClassifier


def test_classifier_preserves_complete_provided_classification() -> None:
    incident = Incident(
        incident_id="INC-1",
        short_description="VPN unavailable",
        description="The VPN cannot connect.",
        category="custom",
        priority=Priority.P2,
    )

    result = RuleBasedIncidentClassifier().classify(incident)

    assert result.category == "custom"
    assert result.priority is Priority.P2
    assert result.source is ClassificationSource.PROVIDED


def test_classifier_infers_missing_category_and_priority() -> None:
    incident = Incident(
        incident_id="INC-2",
        short_description="Remote access unavailable",
        description="The failing service is not known.",
    )

    result = RuleBasedIncidentClassifier().classify(incident)

    assert result.category == "network"
    assert result.priority is Priority.P3
    assert result.source is ClassificationSource.INFERRED


def test_classifier_priority_rules_cover_security_outage_and_default() -> None:
    classifier = RuleBasedIncidentClassifier()

    security = classifier.classify(
        Incident(
            incident_id="INC-3",
            short_description="Unfamiliar account activity",
            description="Possible compromise reported.",
        )
    )
    outage = classifier.classify(
        Incident(
            incident_id="INC-4",
            short_description="Critical application outage",
            description="The service is unavailable for all users.",
        )
    )
    default = classifier.classify(
        Incident(
            incident_id="INC-5",
            short_description="General question",
            description="More information will be provided later.",
        )
    )

    assert (security.category, security.priority) == ("security", Priority.P1)
    assert outage.priority is Priority.P2
    assert (default.category, default.priority) == ("support", Priority.P4)
