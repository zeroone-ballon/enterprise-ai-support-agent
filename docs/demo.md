# End-to-end demo

Start the local API with its API-key-free deterministic generation default:

```bash
uv run uvicorn support_agent.main:app
```

In another terminal, execute the release-candidate scenario:

```bash
uv run python -m support_agent.demo
```

The script creates a unique fictional VPN lockout incident, obtains grounded evidence, records a
human approval using local demo credentials, executes the ServiceNow-compatible sandbox action,
retries with the same idempotency key, and reads the audit trail. It exits non-zero unless:

- approval reaches `approved` before execution;
- execution reports `simulated` and `side_effects: false`;
- the retry returns the identical result;
- audit events are exactly created, approved, and mock-executed.

The default keys are strictly for local demonstration. Command arguments allow alternate base URL
and keys, but real credentials should be supplied through an appropriate secret-handling workflow,
not shell history.
