# Set up the recurring librarian

One real recurring agent run needs an installed runtime and scheduler, verified access,
and observed execution. A prompt, copied config or scheduler example is not a running job.
Use prompts/SCHEDULE-SETUP.md with the user's existing preferences.

## Choose and verify the schedule

Resolve only missing private path, designated host/runtime, cadence, local time, named time
zone, publication authority and notification destination/preferences. Recommend one daily
draft-only run; do not hardcode the user's time zone or backend. Daily executive summaries
are opt-in. Otherwise notify meaningful changes, failures and required decisions only.

Inspect existing jobs and capabilities before configuring. Deduplicate by workspace and
purpose, preserve other jobs and establish single-run concurrency. Use a private owned
worktree, bounded runtime and least necessary source access. Keep credentials in the existing
secret store. Per-clone locks do not exclude other clones/hosts; designate one host or use
scheduler-level coordination.

For native routines, schedule prompts/LIBRARIAN-RUN.md with the actual private path. Verify
supported controls rather than guessing. Do not silently replace a requested native routine
with an OS job. Use actual runtime-supported background roles/controls; preserve the
main/voice model. Prompt wording cannot select a model; record resolved metadata if exposed.

## Local wrapper

`python -m librarian routine` validates the brain, detects pending/flagged records and
overdue pages, locks one clone and invokes the configured agent with an on-disk prompt.
It contains no model, Git credentials, automatic merge or scheduler installer.

Set librarian.json runner.command to an argument array, never a shell string. One argument
must contain {prompt_file}; {root} can appear in arguments. Use a real installed adapter:

```json
{
  "command": ["/absolute/path/to/your-agent-adapter", "--prompt-file", "{prompt_file}", "--workspace", "{root}"],
  "timeout_seconds": 1800
}
```

This is a placeholder, not a bundled executable. Verify actual CLI/authentication/approval
behavior from installed help or official documentation. Do not guess flags or add permission
bypasses. The adapter must honor exit codes and supervise children on timeout.

Run `python -m librarian routine --dry-run`, then a real
`python -m librarian routine --force` and inspect its draft/flag/receipt outcome.
A mock adapter tests the wrapper only. The wrapper fails visibly on missing runner, lock
contention, invalid data, timeout or nonzero exit. Its private logs/last-run state are under
ignored .runtime/. A zero wrapper exit does not prove reconciliation or publication.

Without --force, the wrapper can skip an empty intake with no metadata review due. If the
user opts into daily reporting, schedule routine --force or a separate report job so the
daily artifact is generated even then. Generate one JSON/Markdown artifact with executive
and detailed audit sections; extract the executive summary for separate authorized
distribution and retain the full audit privately.

## Scheduler and daylight saving time

Use templates/cron.example or templates/windows-task.ps1.example only after substituting
verified runtime/private paths and the chosen schedule. Preserve existing crontabs/tasks.
Inspect host and scheduler time-zone support. Verify the next actual run with timestamp,
zone and UTC offset from scheduler evidence.

Record whether the schedule follows local wall time or fixed UTC, including skipped/repeated
hours during daylight-saving transitions. Confirm how repeated-hour duplicates and missed
runs behave; deduplicate/coordinate runs accordingly. Windows and cron semantics depend on
the installed scheduler/host. Do not claim DST support from a text example.

## Proof and handoff

Store non-secret evidence in wiki/operations/automation.md: actual job ID, designated
host/agent, private path, cadence/time/zone, command/reference, verified next timestamp/offset,
DST behavior, concurrency/deduplication, publication scope, notification destination/preference,
owner and disable/remove steps. Update schedule status only from evidence.

A real manual run and first scheduled execution are separate checks. Record the scheduled
run's operator/session/run UUID, start/result and resulting receipts/draft. If it is future,
report scheduled-awaiting-first-run. Do not call verified before observing it. Check failure
visibility and recovery as well. Generate one report artifact, then distribute the extracted
executive summary separately if authorized; reports alone do not send notifications.
Missing access/runtime becomes an explicit blocker while independent
setup continues.
