# Recovery and corrections

Preserve immutable inbox events, receipts and dated evidence. Add corrections under new IDs, with links to the original. A bad published fact gets a reviewed correction or revert; the historical record still says what was published.

If a run stops before committing, inspect the owned worktree. If a PR is open, resume that batch with its owner's authority. If content merged before a published receipt was added, verify the content commit and append the missing receipt. Do not mark an open PR published.

Offline contributors keep safe local outboxes and replay unchanged IDs/content after reconnecting. Historical v1 exact retries remain compatible; new events/receipts use v2. Never migrate by rewriting immutable history: use a new correcting/superseding event with real evidence and attribution. An unavailable source leaves the old verification date unchanged and gets blocked_access. Query failure falls back to the wiki index/files. Never infer current facts from a stale index.

The write lock `.brain-write.lock` and routine lock `.runtime/routine.lock` protect one clone. After a crash, inspect the stored PID/time and verify the original process has exited before removing a stale lock. Do not delete a lock because it is old. Atomic writes require a filesystem supporting hard links; unsupported storage fails instead of overwriting a record.

The routine's `.runtime/last-run.json` records wrapper completion and runner exit code. A zero exit code is not proof of successful knowledge publication; inspect the event receipts and Git result. Runner timeout reports failure, and the configured runner must supervise its own child processes. Check those processes before starting another run.

Keep an appropriate private remote/backup, verify access and rehearse restoration in a separate clone. If a secret enters history, stop distribution, involve the authorized operator, rotate it and coordinate history/clone cleanup. Do not repeat the secret in the incident event.
