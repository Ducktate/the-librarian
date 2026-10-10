# Working agent procedure

## Read before work

1. Read the application's applicable instructions and respect checkout ownership. Locate the configured private brain through your verified clone/connector.
2. Record the brain branch, commit and retrieval time. Fast-forward only a clean owned reader clone. Label offline/old copies; never reset another agent's work.
3. Read wiki/index.md, then relevant domain pages. Check status, owner, dates, scope and original sources. Search returns routes to evidence, not authority. Start small; expand for the actual question.
4. Check current work, decisions and flags for conflicts. Use source-repo contracts for code behavior. If access is unavailable, report the limit and continue only work independent of missing facts.

## Submit an update

Submit at a meaningful milestone, handoff or session close when another agent's understanding should change. Do not submit every thought or routine formatting edit.

1. Create an owned contribution branch in the private brain. Copy templates/contribution.json to a temporary file and fill it. Generate a UUID with `python -c "import uuid; print(uuid.uuid4())"`.
2. Include actual agent/session/machine, observed_at with time zone, repository/commit/ticket/PR, affected page IDs, scoped claims, delivery state, source references, proposed change, missing questions, cost impact and decision authority when relevant. For a proposed new page, target brain-index and describe the page; the librarian assigns its stable ID.
3. Run `python -m librarian submit /path/to/event.json`. The UTC observed_at month selects inbox/YYYY/MM/UUID.json. Exact retries are idempotent; changed content under the same ID is rejected. Corrections use a new ID and supersedes_event_id.
4. Review/redact, commit and share through the private repository using existing authorization. Local submission is not a shared receipt. Report local, pushed or merged state accurately.
5. Respond to a librarian question with a new resolving event and original-event reference. Do not edit the original event or receipt.

At closeout, name event IDs and persistence state or say `No material company fact changed.` Do not rewrite the wiki as a contributor. Keep raw secrets/customer material out of the outbox as well as Git. Offline events can stay in an ignored local outbox until safe to submit.

## Bootstrap each agent

Insert this short instruction in each requested agent's actual project instructions, preserving existing rules:

> Before company work, explicitly read BRAIN_PATH/wiki/index.md and BRAIN_PATH/docs/AGENT-PROCEDURE.md, then relevant pages and their sources. Record brain revision/freshness. Submit material updates as immutable events; report their persistence state. Do not rewrite company facts directly as a contributor. If the brain is unavailable, say so. Source-repo contracts and ownership still apply.

Replace BRAIN_PATH with a real accessible path or authorized connector/repository reference. A link is not proof it was loaded. A remote agent may not see your local disk. Test a fresh session with one known fact and one disposable local contribution before marking that reader ready. Record access in wiki/operations/automation.md without credentials.
