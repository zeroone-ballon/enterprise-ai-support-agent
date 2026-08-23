# Portfolio brief

## Problem

Enterprise support automation often hides evidence, mixes recommendation with execution, and makes
provider failure unsafe. This project demonstrates a narrower pattern: auditable decision support
that can abstain, exposes evidence and evaluation signals, and cannot cross the execution boundary
without authenticated human approval.

## What this demonstrates

- Python and FastAPI API design with strict Pydantic contracts
- Ports-and-adapters separation across retrieval, generation, persistence, and execution
- Deterministic retrieval and reproducible gold-case evaluation
- Fail-closed optional LLM generation with provenance and safety checks
- Human approval, role separation, audit history, and durable idempotency
- SQLite migrations and a no-network ServiceNow-compatible sandbox boundary
- Structured observability, readiness, non-root containerization, and CI gates

## Measured release-candidate result

The bundled fictional evaluation contains eight cases covering normal resolution, ambiguity,
insufficient context, no match, stale knowledge, and high-risk security handling. Phase 10's report
must pass all cases, and CI requires at least 90% line coverage. These figures describe this small,
curated demo dataset only and are not claims about production accuracy.

## Five-minute walkthrough

1. Show `/docs`, `/health`, `/ready`, and `/metrics`.
2. Run `python -m support_agent.demo` against the local API.
3. Point out cited evidence, deterministic generation provenance, human approval, the simulated
   no-side-effect receipt, idempotent replay, and the three-event audit trail.
4. Run `python -m support_agent.evaluate` and explain the bounded gold dataset.
5. Open `architecture.md` and `threat-model.md`, emphasizing residual production requirements.
