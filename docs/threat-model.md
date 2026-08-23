# Threat model

## Scope and assets

Protected assets are incident content, approved knowledge, role credentials, recommendation state,
audit history, idempotency results, and the integrity of the ServiceNow-compatible action contract.
The PoC has no real ServiceNow credential and performs no external remediation.

| Threat | Existing control | Residual risk / production requirement |
|---|---|---|
| Prompt injection in incident or knowledge | Untrusted-data prompt boundary; strict JSON and citation validation | Provider-side retention and evolving attacks require vendor review and adversarial evals |
| Hallucinated or unsupported guidance | Evidence allow-list, lexical grounding, deterministic fallback | Small lexical dataset is not a semantic or factual guarantee |
| Unsafe security action | High-risk detection disables LLM generation; human approval required | Expand policy taxonomy and obtain security-owner review |
| Credential disclosure | SHA-256 digests only; constant-time comparison; sanitized logs | Use a secret manager, rotation, TLS, and stronger identity federation |
| Role confusion | Reviewer, executor, and auditor roles plus actor consistency | Add organization identity, least privilege, and access reviews |
| Duplicate execution | Durable idempotency key and original-result replay | Define retention and concurrency policy for shared production storage |
| Audit tampering | Ordered append-only application API and durable events | SQLite administrators can alter data; use immutable external audit storage |
| Denial of service | Bounded inputs and provider timeout | Add gateway limits, quotas, backpressure, monitoring, and capacity planning |
| Data exfiltration through logs | No bodies, headers, credentials, incident, or knowledge text in request logs | Validate platform collector configuration and retention |
| Supply-chain compromise | Locked dependencies and CI quality gates | Add dependency scanning, image signing, SBOM, and provenance attestation |

## Explicit non-claims

This repository is a portfolio release candidate, not a certified production system. It has not
undergone penetration testing, privacy impact assessment, formal threat-model review, ServiceNow
integration certification, disaster-recovery testing, or regulated-data approval.
