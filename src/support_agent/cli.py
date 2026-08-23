"""Small Phase 4 command-line interface for inspecting retrieval evidence."""

import argparse
import json
from pathlib import Path
from typing import Any

from support_agent.adapters.json_knowledge_repository import JsonKnowledgeRepository
from support_agent.domain.incident import Incident
from support_agent.services.lexical_retriever import WeightedLexicalRetriever


def _load_incident(path: Path, incident_id: str) -> Incident:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    for item in raw:
        if item.get("incident_id") == incident_id:
            return Incident.model_validate(item)
    raise SystemExit(f"incident not found: {incident_id}")


def main() -> None:
    """Search demo knowledge for one incident and print JSON evidence."""

    parser = argparse.ArgumentParser(description="Search demo support knowledge")
    parser.add_argument("incident_id", help="Demo incident ID, for example INC-DEMO-001")
    parser.add_argument(
        "--incidents",
        type=Path,
        default=Path("data/incidents.json"),
        help="Incident JSON path",
    )
    parser.add_argument(
        "--knowledge",
        type=Path,
        default=Path("data/knowledge.json"),
        help="Knowledge JSON path",
    )
    args = parser.parse_args()

    incident = _load_incident(args.incidents, args.incident_id)
    repository = JsonKnowledgeRepository.from_path(args.knowledge)
    retriever = WeightedLexicalRetriever(repository)
    evidence = retriever.search(incident)
    print(json.dumps([item.model_dump(mode="json") for item in evidence], indent=2))


if __name__ == "__main__":
    main()

