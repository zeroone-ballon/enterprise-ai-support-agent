# Enterprise AI Support Agent

Enterprise AI Support Agent is an auditable IT support decision-support PoC. It will retrieve relevant knowledge, propose grounded responses and next actions, evaluate risk, and hold actions for human approval.

Phase 5 provides the first end-to-end, deterministic `/assist` workflow: incident classification, explainable Top-3 retrieval, grounded recommendation or explicit abstention, safety evaluation, confidence, and mandatory human approval.

## Requirements

- Python 3.11 or later

## Setup with uv

```bash
uv python install 3.12
uv sync --extra dev
```

Optional local configuration:

```bash
cp .env.example .env
```

No API key is required for Phase 5.

## Run

```bash
uv run uvicorn support_agent.main:app --reload
```

Open the API documentation at <http://127.0.0.1:8000/docs> or verify health:

```bash
curl http://127.0.0.1:8000/health
```

Expected health response:

```json
{
  "status": "ok",
  "service": "Enterprise AI Support Agent",
  "version": "0.1.0",
  "environment": "development"
}
```

Submit a demo incident to the assistance workflow:

```bash
curl -s http://127.0.0.1:8000/assist \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "INC-LIVE-001",
    "short_description": "VPN account locked after repeated sign-in attempts",
    "description": "The corporate VPN reports that the account is locked.",
    "category": "access",
    "priority": "P3"
  }'
```

The assistance response includes classification, recommendation or abstention, Top-3 evidence, evaluation signals, confidence, and approval state. It always remains `pending_approval`; Phase 5 does not execute changes.

## Test and lint

```bash
uv run pytest
uv run ruff check .
```

## Project structure

```text
enterprise-ai-support-agent/
├── src/support_agent/
│   ├── api/             # HTTP routes and schemas
│   ├── adapters/        # External system implementations
│   ├── domain/          # Business models and policies
│   ├── services/        # Application workflows
│   ├── config.py        # Runtime configuration
│   └── main.py          # FastAPI application factory
├── tests/
├── data/                # Fictional incidents, knowledge, and gold outcomes
├── docs/                # Design notes for the demo and evaluation data
├── .env.example
├── .python-version
├── uv.lock
└── pyproject.toml
```

The `adapters`, `domain`, and `services` packages keep infrastructure, business rules, and workflows separate.

## Implemented phases

### Phase 1 — Application foundation

- [x] Installable `src`-layout Python project
- [x] FastAPI application factory
- [x] `GET /health`
- [x] Typed health response
- [x] Automated health and OpenAPI tests
- [x] API-key-free startup
- [x] Reproducible setup, run, test, and lint commands

### Phase 2 — Domain model

- [x] Strict incident intake and classification models
- [x] Knowledge lifecycle and evidence models
- [x] Recommendation and explicit abstention models
- [x] Evaluation signals
- [x] Human approval audit metadata
- [x] Aggregate `AssistResponse`
- [x] Cross-model grounding and confidence invariants
- [x] Automated validation tests

### Phase 3 — Demo and evaluation data

- [x] Eight fictional incidents
- [x] Eleven fictional knowledge articles
- [x] Gold retrieval and safety outcomes
- [x] Primary, ambiguous, insufficient-context, no-match, stale, and high-risk cases
- [x] Draft and retired articles for retrieval-exclusion tests
- [x] Deterministic freshness reference date
- [x] Automated fixture and reference-integrity tests

### Phase 4 — JSON repository and retriever

- [x] Domain-facing `KnowledgeRepository` and `Retriever` contracts
- [x] Strict UTF-8 JSON repository with duplicate and validation checks
- [x] Draft and retired article exclusion
- [x] Weighted title, tag, content, and category scoring
- [x] Explainable matched terms and bounded scores
- [x] Deterministic Top-3 ordering and configurable threshold
- [x] Top-1, Top-3 recall, and no-match evaluation metrics
- [x] Command-line retrieval inspection

### Phase 5 — Deterministic assistance workflow

- [x] Rule-based classification with provided/inferred provenance
- [x] `POST /assist` with a typed OpenAPI contract
- [x] Grounded recommendation from published, current knowledge
- [x] Explicit abstention for missing, ambiguous, or stale evidence
- [x] Freshness, context, grounding, and high-risk evaluation signals
- [x] Evidence-derived confidence
- [x] Mandatory `pending_approval` state with no execution side effects
- [x] Gold-case workflow and HTTP contract tests

## Next phase

Phase 6 will add approval and rejection transitions plus an append-only audit trail and mock execution boundary.

## Inspect Phase 4 retrieval

```bash
uv run python -m support_agent.cli INC-DEMO-001
```

The command prints up to three ranked `Evidence` objects with the article ID, score, matched terms, publication state, and update date.
