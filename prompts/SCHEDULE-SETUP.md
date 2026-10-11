# Configure and verify the librarian schedule

Configure one recurring draft-only librarian job for the private brain using my authorized
environment. Reuse existing preferences; resolve only missing private path, designated
host/runtime, cadence, time, time zone, notification destination and whether I want daily
executive summaries. Default notifications to meaningful changes, failures and required
decisions. Do not assume a time zone, platform or model provider.

Read docs/SCHEDULING.md. Inspect the installed scheduler/runtime capabilities and existing
jobs first. Preserve them and avoid duplicate librarian jobs. Use a supported native
routine when requested; do not hide an OS scheduler substitution. Use an owned workspace,
bounded runtime, existing credential storage and single-run concurrency. Per-clone locks
do not exclude another host: establish scheduler/host coordination before enabling both.

Use prompts/LIBRARIAN-RUN.md with the real private path. Preserve the main/voice runtime;
use only actual backend-supported background roles or explicit runtime controls. The
runner is an adapter to an installed agent, not a model included in this template.

Verify the job ID, command/reference, cadence, named time zone, next timestamp and UTC
offset from scheduler evidence. Check DST semantics: whether the chosen time follows
local wall time, what happens in skipped/repeated hours and how duplicates are prevented.
Record notification destination/preferences, publication scope, owner and disable steps.

Run a dry run and one real manual agent run, checking the draft/flag/receipt outcome and
failure reporting. Then observe the first real scheduled execution with its actual run
identity and outcome. If it is future, label scheduled-awaiting-first-run and keep that
checkpoint open. Configuration files and mock runs do not prove scheduling or reconciliation.

Generate one daily JSON or Markdown report artifact with explicit date/time zone/as-of
cutoff and separate executive/audit sections. Extract the executive summary for separate
distribution; retain the detailed audit in the private brain. When daily reporting is
opted in, use routine --force or a separate report job so an empty intake queue does not
skip the report. Send summaries only when opted in and to the authorized destination.
Finish with verified schedule evidence and precise blockers; do not call the scheduler
operational before the first scheduled run is observed.
