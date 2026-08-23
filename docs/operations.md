# Operations and deployment boundary

Phase 10 keeps the PoC deployable without claiming production readiness.

- `/health` is a liveness probe and does not touch dependencies.
- `/ready` checks that knowledge is readable and the SQLite location is writable.
- `/metrics` exposes sanitized, process-local request counts and latency. It never stores headers,
  bodies, API keys, incident text, or knowledge text.
- Every HTTP response carries `X-Request-ID`; a supplied ID is propagated for correlation.
- Production startup rejects the bundled development API-key digests.
- The container runs as a non-root user and expects durable SQLite state at `/app/state`.
- Structured logs are JSON, but retention, collection, alerting, TLS, rate limiting, backup,
  secret rotation, and multi-instance storage remain platform responsibilities.

Generate the deterministic evaluation artifact with:

```bash
uv run python -m support_agent.evaluate --output reports/evaluation.json
```

The command exits non-zero if any gold case fails, so the same quality gate is usable locally and
in CI.
