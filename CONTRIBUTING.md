# Contributing

This public upstream contains a reusable workflow. Never submit a populated private brain,
real inbox/receipt history, private URLs or configuration secrets. Use fictional identities,
data and examples.invalid domains. Ducktate brand links identify the public template only.

Work on an owned branch, preserve unrelated edits and respect applicable instructions.
Run `python -m librarian validate` and `python -m unittest discover -s tests -v`.
Explain changed behavior, verification limits and migration in the PR. Keep runtime
dependencies Python 3.11+ standard library unless a documented need justifies more.

New events/receipts use v2; retained v1 records remain readable and immutable. Test exact
retries and correction behavior when changing intake/history. Document actual command
flags, errors and report scope. Do not promise installed runtimes or schedules from fixtures.

Keep template policy generic. Owners choose their private publication authority and review
checks; do not hardcode a private CI exception, provider, model, time zone or notification
destination. Report bugs with sanitized reproductions. If a secret is exposed, rotate it
with its provider and contact the responsible owner through an authorized channel.
