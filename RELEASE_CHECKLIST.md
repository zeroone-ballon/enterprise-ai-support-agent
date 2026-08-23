# Release candidate checklist

- [ ] `uv sync --extra dev --locked`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] Full tests pass with at least 90% coverage
- [ ] Gold evaluation reports 8/8 passed
- [ ] Live end-to-end demo passes and reports no side effects
- [ ] `/health`, `/ready`, `/metrics`, request ID, and sanitized JSON logs verified
- [ ] Production startup rejects demonstration credential digests
- [ ] Non-root container builds and reports a healthy readiness probe
- [ ] No `.env`, database, report, credential, cache, or backup file is tracked
- [ ] Architecture, threat model, operations, demo, and portfolio documentation reviewed
- [ ] GitHub Actions passes on the release-candidate commit
- [ ] Annotated Git tag `v1.0.0-rc.1` created only after CI succeeds
