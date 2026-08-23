# Phase 9 generation safety boundary

Phase 9 does not make an LLM authoritative. Retrieval, freshness, sufficiency, risk classification, approval, and execution state remain deterministic application policies.

## Default behavior

`GENERATION_MODE=deterministic` copies the current approved knowledge procedure into the proposed response. It does not require an API key or make a network request.

## Optional provider behavior

`GENERATION_MODE=llm` may draft presentation text through an explicitly configured OpenAI-compatible endpoint. Incident and knowledge values are serialized as untrusted data. The response must validate against the strict `GeneratedDraft` model.

## Fail-closed checks

Provider output is discarded when any of these conditions occurs:

- transport, timeout, response-shape, JSON, or validation failure;
- omission of the top retrieved evidence;
- citation of a knowledge ID outside the retrieved evidence;
- insufficient lexical overlap with the approved source article;
- an explicitly unsafe instruction;
- classification of the incident as high risk.

The system then uses the deterministic draft, sets `fallback_used=true`, and records violations in both `generation.violations` and `evaluation.violations`.

## Deliberate limitations

Lexical grounding is not semantic entailment. The guardrail reduces obvious unsupported output but cannot prove every sentence. Human approval remains mandatory, provider output cannot execute an action, and the ServiceNow adapter remains sandbox-only.
