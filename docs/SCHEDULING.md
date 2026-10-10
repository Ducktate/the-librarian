# Set up the recurring librarian

The goal is one real recurring agent run with evidence of its schedule and operation. A prompt file or cron example alone is not a running librarian. Prefer the user's existing agent routine/automation scheduler when available. Otherwise use their OS scheduler with the local wrapper below.

## Decide once, then configure

Use existing user preferences. Resolve only missing company path, designated host/agent, source access, time zone, cadence, runtime and publication authority. Recommend one daily draft-only run plus the user's ordinary review cadence; do not silently assume a time zone. Use a private owned worktree and restrict the runner to needed resources. Keep credentials in the user's existing secret store.

For native agent routines, schedule prompts/LIBRARIAN-RUN.md as instructions with the absolute private brain path. Configure single-run concurrency, a bounded runtime, failure visibility and no notifications for unchanged state unless requested. Verify native task ID, cadence/time zone and next-run timestamp. Do not install an OS cron as a hidden replacement for an unavailable native routine.

## Local wrapper

The alternative `python -m librarian routine` validates the brain, detects pending/flagged events and overdue pages, acquires a per-clone lock, and invokes the configured agent command with an on-disk run prompt. It does not contain a model, Git credentials, automatic merge or a scheduler installer.

Edit the runner section of librarian.json in your private copy. `command` is an argument array, never a shell string. One argument must contain `{prompt_file}`; `{root}` may appear in any argument. Use an adapter for your installed agent that reads the prompt file and executes a bounded agent turn. Verify the actual runtime's supported command/authentication/approval behavior from its installed help or official docs. Do not guess flags or add bypass-permission options. Credentials must not appear in the array.

```json
{
  "command": ["/absolute/path/to/your-agent-adapter", "--prompt-file", "{prompt_file}", "--workspace", "{root}"],
  "timeout_seconds": 1800
}
```

That path is a placeholder, not a bundled executable. The adapter should honor exit codes and supervise/stop its children on timeout. A mock adapter tests the wrapper only; it does not qualify a real agent.

Run `python -m librarian routine --dry-run`. Then run `python -m librarian routine --force` with the real configured runtime and verify its draft/flag result. The routine exits 0 on an empty, non-stale queue; it fails visibly for missing runner, lock contention, validation error, timeout or nonzero runner exit. Failure details and last-run state remain locally under ignored .runtime/. Logs can contain private output and must not be published.

## OS scheduler examples

Use templates/cron.example or templates/windows-task.ps1.example after replacing absolute paths and selecting the user's schedule. Preserve all existing jobs; never replace an entire crontab. Cron time zones differ by installation: inspect the host time zone and scheduler support, then verify the displayed next run. Windows Task Scheduler uses the host's schedule/time-zone behavior; verify that it matches the chosen time zone, including daylight-saving changes. Use a non-overlapping task policy and an appropriate dedicated account; do not embed passwords.

## Proof and handoff

Store non-secret scheduler evidence in wiki/operations/automation.md: actual job ID, host/agent, configured path, time zone, cadence, command/reference, next run, last observed scheduled execution and result, publication scope, notification behavior, owner and disable/remove instructions. Update librarian.json schedule status only from this evidence. A manual run and a scheduled run are separate acceptance checks. If the first scheduled execution is later, report scheduled-awaiting-first-run and keep that checkpoint open.

Do not call setup complete until the requested agent has actually read the brain, submitted an update, reconciled or flagged it, and the recurring job has been verified. Missing permissions/runtime access become explicit blockers; continue independent setup work.
