# ServiceNow PDI integration

This opt-in adapter is for a Personal Developer Instance and fictional incidents only. Sandbox
execution remains the default.

## Boundary

1. The API incident ID must be the exact ServiceNow incident number.
2. A reviewer approves the grounded recommendation.
3. An executor supplies an idempotency key.
4. The adapter queries at most two incidents and requires exactly one exact-number match.
5. The adapter patches only `work_notes` on the resolved `sys_id`.
6. The receipt and audit event explicitly report a real PDI side effect.

Use a dedicated web-service user with the minimum table and field ACLs. Basic authentication is
limited to the PDI proof of concept; migrate to OAuth and managed secrets before any broader use.

## Known crash window

Normal retries with the same idempotency key return the stored result and do not repeat the PATCH.
There is still a narrow failure window if PDI accepts the PATCH but the local process stops before
the SQLite result commits. Production-grade exactly-once behavior requires a durable outbox and a
PDI correlation field or a dedicated idempotent Scripted REST API.
