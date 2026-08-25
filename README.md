# Enterprise AI Support Agent

Enterprise AI Support Agent is an auditable IT support decision-support PoC. It will retrieve relevant knowledge, propose grounded responses and next actions, evaluate risk, and hold actions for human approval.

Version `1.0.0rc1` completes the portfolio release candidate with a live end-to-end demo,
architecture and threat-model documentation, a security policy, and an explicit release checklist.
The optional structured LLM boundary remains fail-closed, while deterministic behavior stays the
API-key-free default.

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

The default `GENERATION_MODE=deterministic` requires no LLM key and makes no provider call. Optional OpenAI-compatible generation is enabled only when `GENERATION_MODE=llm`, `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` are all configured.

## Run

```bash
uv run uvicorn support_agent.main:app --reload
```

Open the API documentation at <http://127.0.0.1:8000/docs> or verify health:

```bash
curl http://127.0.0.1:8000/health
```

Readiness and sanitized process metrics are available separately:

```bash
curl -i http://127.0.0.1:8000/ready
curl -s http://127.0.0.1:8000/metrics
```

Responses carry an `X-Request-ID`. Request logs contain method, route template, status, duration,
and request ID, but never headers, request bodies, incident text, knowledge text, or credentials.

Expected health response:

```json
{
  "status": "ok",
  "service": "Enterprise AI Support Agent",
  "version": "1.0.0rc1",
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

Phase 9 also exposes generation provenance:

```json
{
  "generation": {
    "mode": "deterministic",
    "provider": "deterministic",
    "fallback_used": false,
    "violations": []
  }
}
```

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

## Optional ServiceNow PDI execution

The default `EXECUTION_MODE=sandbox` makes no network call. On an isolated Personal Developer
Instance only, `EXECUTION_MODE=servicenow_pdi` resolves the submitted `incident_id` as an exact
ServiceNow incident number and updates only `work_notes` after authenticated human approval. The
receipt then reports `"status":"completed"` and `"side_effects":true`.

```env
EXECUTION_MODE=servicenow_pdi
SERVICENOW_INSTANCE_URL=https://devXXXXX.service-now.com
SERVICENOW_USERNAME=replace-with-integration-user
SERVICENOW_PASSWORD=use-a-local-secret
SERVICENOW_TIMEOUT_SECONDS=10
```

Never commit these values. PDI mode rejects non-HTTPS, non-`service-now.com`, and path-bearing
origins; fails closed on timeout, malformed JSON, non-2xx responses, and zero or multiple incident
matches; and never logs the Authorization header. The initial adapter intentionally does not change
state, assignment, priority, or custom fields.

## Test and lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m support_agent.evaluate --output reports/evaluation.json
```

The evaluation command checks all eight fictional gold cases and exits non-zero on any mismatch.
The CI workflow additionally enforces at least 90% test coverage.

## AI Review Console

The read-only Next.js console in `frontend/` defaults to three local demo cases and can optionally
load one fictional PDI Incident. It displays classification, recommendation, evaluation, and ranked
evidence. Both modes proxy requests through server routes so the browser does not need direct
FastAPI network access. Local Demo remains available when the PDI is sleeping or unavailable.

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Keep FastAPI running at `http://127.0.0.1:8000`, or set `FASTAPI_BASE_URL` in `.env.local`.
Reviewer credentials are read only by the Next.js server route. Never prefix these variables with
`NEXT_PUBLIC_`, which would expose them to browser JavaScript. The checked-in values are local demo
credentials whose SHA-256 digests are already the FastAPI development defaults.
Executor and auditor credentials follow the same server-only boundary. The console reuses one
generated idempotency key for execution retries and renders the resulting append-only audit trail.

## End-to-end release-candidate demo

With the API running in one terminal, execute the complete local scenario in another:

```bash
uv run python -m support_agent.demo
```

The command verifies grounded assistance, authenticated human approval, simulated execution,
idempotent retry, a three-event audit trail, and the absence of external side effects. See
`docs/demo.md` for the walkthrough and `docs/portfolio.md` for a concise project narrative.

## Container

Build the non-root image:

```bash
docker build -t enterprise-ai-support-agent:phase10 .
```

The image uses `APP_ENV=production`, so it intentionally refuses to start with the bundled demo
credential digests. Supply three separately generated SHA-256 digests and mount durable state:

```bash
docker run --rm -p 8000:8000 \
  -v support-agent-state:/app/state \
  -e REVIEWER_API_KEY_SHA256='<sha256>' \
  -e EXECUTOR_API_KEY_SHA256='<sha256>' \
  -e AUDITOR_API_KEY_SHA256='<sha256>' \
  enterprise-ai-support-agent:phase10
```

See `docs/operations.md` for the explicit deployment boundary and platform responsibilities.

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

### Phase 9 — Structured LLM generation and guardrails

- [x] Provider-neutral structured recommendation-generation port
- [x] Deterministic generation remains the API-key-free default
- [x] Optional OpenAI-compatible chat-completions adapter
- [x] Strict Pydantic validation of provider JSON
- [x] Allowed evidence citation enforcement
- [x] Minimum lexical grounding against approved knowledge
- [x] Explicit unsafe-instruction rejection
- [x] LLM generation disabled for high-risk incidents
- [x] Provider timeout, malformed response, and configuration fallback
- [x] Generation mode, provider, fallback, and violation provenance
- [x] Provider incident and knowledge content treated as untrusted data

### Phase 10 — Evaluation, observability, and deployment hardening

- [x] Reproducible eight-case JSON evaluation report with non-zero failure exit
- [x] Top-1, abstention, grounding, freshness, and high-risk metrics
- [x] Sanitized structured request logs and propagated request IDs
- [x] Process-local request count, failure, and latency metrics
- [x] Separate liveness and dependency-readiness endpoints
- [x] Production startup rejects bundled development credential digests
- [x] Non-root container with health check and durable state boundary
- [x] GitHub Actions lint, format, coverage, evaluation, and artifact gates
- [x] Explicit deployment limitations and platform responsibilities

### Phase 11 — Release candidate and portfolio packaging

- [x] Live standard-library end-to-end demonstration command
- [x] Final approval, execution, replay, audit, and sandbox acceptance test
- [x] Release-candidate version exposed by health and OpenAPI
- [x] Architecture and runtime-flow diagrams
- [x] Threat model with residual production requirements
- [x] Five-minute portfolio walkthrough and measured claims
- [x] Security policy, changelog, MIT license, and release checklist
- [x] Explicit no-side-effect and non-production-use boundaries

## Release status

All eleven planned phases are implemented. `1.0.0rc1` remains a portfolio release candidate rather
than a production-certified support system. Promotion to a final release requires the checks in
`RELEASE_CHECKLIST.md` and independent security, privacy, platform, and operational review.

## Inspect Phase 4 retrieval

```bash
uv run python -m support_agent.cli INC-DEMO-001
```

The command prints up to three ranked `Evidence` objects with the article ID, score, matched terms, publication state, and update date.
