# Demo data design

Phase 3 provides fictional data for deterministic retrieval and safety evaluation. It contains no customer data, personal data, credentials, real hostnames, or executable integration details.

## Files

- `data/incidents.json`: eight input incidents validated by the `Incident` model.
- `data/knowledge.json`: eleven articles validated by the `KnowledgeArticle` model.
- `data/gold_cases.json`: expected classification, retrieval, abstention, freshness, and risk outcomes.

## Case matrix

| Incident | Case | Expected behavior |
| --- | --- | --- |
| `INC-DEMO-001` | VPN lockout | Rank `KB-DEMO-001` and recommend identity-verified unlock steps. |
| `INC-DEMO-002` | Microsoft 365 loop | Rank `KB-DEMO-003` and avoid an unnecessary password reset. |
| `INC-DEMO-003` | Low disk space | Rank `KB-DEMO-005`, not the encryption-key article. |
| `INC-DEMO-004` | Ambiguous remote access | Cite triage guidance and abstain from remediation. |
| `INC-DEMO-005` | Insufficient context | Request diagnostic information and abstain. |
| `INC-DEMO-006` | No match | Return no evidence and abstain. |
| `INC-DEMO-007` | Stale knowledge | Detect the old article and require specialist review. |
| `INC-DEMO-008` | High risk | Preserve MFA and require approval for containment. |

## Retrieval exclusions

`KB-DEMO-010` is retired and `KB-DEMO-011` is a draft. A retriever must exclude both even when their terms closely match an incident.

## Freshness rule

The gold dataset uses `2026-08-23` as its fixed reference date and 365 days as the maximum article age. Fixing the date keeps evaluation deterministic. Production code should receive the current time through an injectable clock rather than reading it directly inside the domain logic.

## Intended Phase 4 metrics

- Top-1 accuracy across cases with an expected top article.
- Top-3 recall across all listed relevant article IDs.
- 100% exclusion of draft and retired articles.
- 100% abstention for ambiguous, insufficient-context, no-match, and stale-only cases.
- 100% detection of high-risk cases.

