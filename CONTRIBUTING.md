# Contributing

The public upstream contains the reusable workflow only. Do not open a PR with a populated private company brain or real inbox records. Use examples.invalid domains, generic identities and fictional fixtures.

Work on a branch, preserve unrelated edits, and run `python -m librarian validate` plus `python -m unittest discover -s tests -v`. Explain changed behavior, validation and any format migration in the PR. Runtime dependencies should remain Python 3.11+ standard library unless a documented need justifies more.

Report bugs with a minimal sanitized reproduction. Do not include secrets in issues; if one is exposed, rotate it with its provider and contact the responsible account owner through an authorized channel.
