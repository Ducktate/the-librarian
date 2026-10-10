---
schema_version: 1
id: "brain-index"
title: "Your Company brain"
type: "reference"
domain: "company"
owner: "unassigned"
maintainer: "librarian"
status: "draft"
confidentiality: "internal"
sources: ["docs/OPERATING-POLICY.md"]
last_verified: null
verified_scope: "Unconfigured starter. No company facts verified."
review_every_days: 14
review_trigger: "Relevant source, owner, contract, decision or runtime changes"
related_ids: []
supersedes: []
superseded_by: []
---

# Your Company brain

This is the entrypoint for Your Company. This unconfigured template contains no verified company facts. Read relevant pages, check their status/owner/sources/verification scope, then inspect original evidence. Do not load the entire wiki for every question.

| Need | Page |
| --- | --- |
| Company and product | [Company overview](company/overview.md) |
| Code and shared contracts | [Repository map](engineering/repositories.md) |
| Hosting and services | [Service register](infrastructure/services.md) |
| Actuals, forecasts and budgets | [Cost register](operations/costs.md) |
| Ownership and decision authority | [Ownership](operations/ownership.md), [decisions](decisions/index.md) |
| Current work | [Work links](operations/active-work.md) |
| Agent and recurring-job readiness | [Automation register](operations/automation.md) |
| Reading and updates | [Agent procedure](../docs/AGENT-PROCEDURE.md) |
| Filing and questions | [Librarian procedure](../docs/LIBRARIAN-PROCEDURE.md) |

Run `python -m librarian queue` for unresolved events and receipts. Search is a route to evidence, not proof. Record the brain commit and freshness at task start. Submit material changes through your own contribution branch; report persistence at handoff.
