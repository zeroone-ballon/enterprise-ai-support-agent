# Enterprise AI Support Agent

Enterprise AI Support Agent is an auditable IT support decision-support PoC. It will retrieve relevant knowledge, propose grounded responses and next actions, evaluate risk, and hold actions for human approval.

Phase 8 hardens the integration boundary. Versioned SQLite migrations preserve existing Phase 7 data, only API-key hashes are configured, and approved actions are translated into a ServiceNow-compatible sandbox outbox without making an HTTP request.

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
set -a
source .env
set +a
```

`POST /assist` remains API-key-free for the local demo. Recommendation review, execution, retrieval, and audit endpoints require role keys. The server stores only SHA-256 digests; replace all development credentials outside local demonstration.

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

The assistance response includes classification, recommendation or abstention, Top-3 evidence, evaluation signals, confidence, and approval state. It starts as `pending_approval` and never performs an external action.

Approve and safely simulate execution using the returned recommendation ID:

```bash
curl -s http://127.0.0.1:8000/recommendations/REC-INC-LIVE-001/approve \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-reviewer-key' \
  -d '{"reviewer":"service-desk-lead","reason":"Evidence verified"}'

curl -s http://127.0.0.1:8000/recommendations/REC-INC-LIVE-001/execute \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-executor-key' \
  -H 'Idempotency-Key: demo-execution-001' \
  -d '{"executor":"automation-operator"}'

curl -s http://127.0.0.1:8000/recommendations/REC-INC-LIVE-001/audit \
  -H 'X-API-Key: dev-auditor-key'
```

The execution receipt always reports `"status":"simulated"` and `"side_effects":false`. Repeating execution with the same `Idempotency-Key` returns the original result without adding another audit event. SQLite state remains available after the application restarts.

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

### Phase 6 — Approval, audit, and mock execution

- [x] Explicit pending → approved → executed state machine
- [x] Explicit pending → rejected terminal transition
- [x] Approval blocked for abstained recommendations
- [x] Execution blocked unless a human first approves
- [x] Required reviewer, rejection reason, executor, and timestamps
- [x] Append-only, contiguous audit event history
- [x] In-memory lifecycle repository behind a domain port
- [x] Mock executor behind an execution port
- [x] Simulation receipt proving no external side effects
- [x] HTTP 404, 409, and 422 error contracts

### Phase 7 — Durable, authenticated, idempotent lifecycle

- [x] SQLite persistence for recommendations and ordered audit events
- [x] State restoration after application restart
- [x] Reviewer, executor, and auditor API-key roles
- [x] Authenticated actor and request actor consistency checks
- [x] HTTP 401 and 403 authorization contracts
- [x] Required execution `Idempotency-Key`
- [x] Persistent idempotent execution results across restarts
- [x] Duplicate retries return the original receipt without duplicate audit events
- [x] SQLite and execution adapters remain behind domain ports

### Phase 8 — Migration and ServiceNow sandbox boundary

- [x] Ordered SQLite schema migrations with applied-version history
- [x] Safe upgrade of an existing Phase 7 database without data loss
- [x] SHA-256 API-key digest configuration with constant-time comparison
- [x] No plaintext API keys in server settings
- [x] Typed ServiceNow-compatible incident update contract
- [x] Durable local sandbox outbox
- [x] Recommendation, evidence, work-note, and correlation mappings
- [x] No ServiceNow URL, credential, or network call
- [x] Contract and migration regression tests

## Next phase

## Remaining roadmap

- **Phase 9:** optional LLM provider boundary, structured generation, grounding guardrails, and deterministic fallback
- **Phase 10:** evaluation report, observability, containerization, CI, and deployment hardening
- **Phase 11:** final end-to-end demo, architecture and threat-model documentation, portfolio packaging, and release candidate

## Inspect Phase 4 retrieval

```bash
uv run python -m support_agent.cli INC-DEMO-001
```

The command prints up to three ranked `Evidence` objects with the article ID, score, matched terms, publication state, and update date.
