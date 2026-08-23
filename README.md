# Enterprise AI Support Agent

Enterprise AI Support Agent is an auditable IT support decision-support PoC. It will retrieve relevant knowledge, propose grounded responses and next actions, evaluate risk, and hold actions for human approval.

Phase 1 provides the FastAPI application foundation and health endpoint. It intentionally does not implement incident assistance yet.

## Requirements

- Python 3.11 or later

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Optional local configuration:

```bash
cp .env.example .env
```

No API key is required for Phase 1.

## Run

```bash
uvicorn support_agent.main:app --reload
```

Open the API documentation at <http://127.0.0.1:8000/docs> or verify health:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Enterprise AI Support Agent",
  "version": "0.1.0",
  "environment": "development"
}
```

## Test and lint

```bash
pytest
ruff check .
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
├── .env.example
└── pyproject.toml
```

The empty `adapters`, `domain`, and `services` packages are intentional architecture boundaries for later phases.

## Phase 1 acceptance criteria

- [x] Installable `src`-layout Python project
- [x] FastAPI application factory
- [x] `GET /health`
- [x] Typed health response
- [x] Automated health and OpenAPI tests
- [x] API-key-free startup
- [x] Reproducible setup, run, test, and lint commands

## Next phase

Phase 2 will add the `Incident`, `KnowledgeArticle`, `Evidence`, `Recommendation`, `Approval`, and `AssistResponse` domain models defined in the Phase 0 specification.

