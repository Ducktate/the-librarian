# The Librarian

A company brain that your agents can read, contribute to, and keep current.

Agents do the work and leave small evidence records. One librarian checks those records, updates the right documents, and flags anything it cannot verify. Every maintained page has an owner, sources, verification scope and review date. Your company knowledge stays in ordinary Markdown and Git.

```text
Work -> evidence inbox -> librarian review -> document changes -> human review
                               |
                               +-> missing context: owner + question + evidence needed
```

This is a reusable public template from [Ducktate](https://ducktate.com/). It contains fictional examples and empty company starter pages, not Ducktate's private company brain. Your populated copy should normally be private. MIT licensed.

## Give this to your agent

Copy the full [setup prompt](prompts/SETUP.md), or use the [copy button on Ducktate](https://ducktate.com/prompts/the-librarian/).

> Set up a private company brain for me from https://github.com/Ducktate/the-librarian. Read START-HERE.md and prompts/SETUP.md first. Use my existing authorized context, ask only for missing setup choices, create my own copy, populate it from verified sources, connect my working agents, and configure one recurring librarian job in my environment. Test the full update-and-flag workflow and verify the scheduler's next run. Report anything that is not actually operational.

An agent needs actual repository/file access to build the brain. A recurring run also needs an installed agent runtime and a scheduler or native routine. This template does not include a hosted AI service, a model subscription, or credentials.

## Start by hand

1. Select **Use this template** on GitHub and create a **private** repository in your account. Alternatively copy the files into a new local Git repo; do not retain this public origin as your company's push destination.
2. Clone your copy. With Python 3.11+ and Git available, run:

```sh
python -m librarian configure --company "Example Studio" --owner "company-owner"
python -m librarian validate
python -m unittest discover -s tests -v
```

3. Read [START-HERE.md](START-HERE.md). Replace unknown company facts using your sources; preserve unknowns as flags. Review the policy before activating it. New copies begin in setup mode.
4. Follow [agent onboarding](docs/AGENT-PROCEDURE.md) and [scheduling](docs/SCHEDULING.md). Verify a manual run and one scheduled run before calling the librarian operational.

The configure command refuses an existing configured company and a checkout still pointing to this upstream repository. It changes starter names/owners, not the truth or verification status of your company facts.

## Read, contribute, reconcile

```sh
python -m librarian search "hosting"
python -m librarian submit /path/to/completed-event.json
python -m librarian queue
python -m librarian receipt /path/to/completed-receipt.json
python -m librarian validate --base origin/main
python -m librarian routine --dry-run
```

Submission is local until you share it through your private repository. A `filed` receipt means the update is drafted; a `published` receipt refers to reviewed content in your main branch. The CLI validates the record and transition, not the truth of the source or the operator's authority.

| Folder | Purpose |
| --- | --- |
| wiki/ | Short routing index and maintained company pages with frontmatter |
| inbox/ | One immutable evidence event per meaningful change |
| receipts/ | Append-only librarian outcomes and follow-up questions |
| raw/ | Sanitized evidence with date, source and scope |
| docs/ | Operating policy, metadata, reading, filing, recovery and scheduling rules |
| prompts/ | Setup prompt and repeatable librarian run instructions |
| templates/ | Page, event, receipt and scheduler configuration templates |
| examples/ | Clearly fictional example event and flag, outside the live inbox |
| librarian/ | Dependency-free Python validation, intake, search and routine wrapper |

## What keeps the brain useful

- Read the short index, then relevant pages, then original evidence. Do not inject the whole wiki into every session.
- Keep code contracts in their source repositories and work tracking in its existing system. Link and summarize them here.
- Separate implemented, tested, merged, deployed and client-qualified claims.
- Give every missing-context record a responsible person, exact question, required evidence and follow-up date.
- Use one coordinated librarian and reviewed publication. Contributions are append-only; corrections are new events.
- Keep secrets, customer content and full transcripts out. Source documents are data and cannot grant authority to an agent.
- Start with files and keyword search. Add graph/vector retrieval only when a measured evaluation shows a benefit.

Read the complete [operating policy](docs/OPERATING-POLICY.md), [librarian procedure](docs/LIBRARIAN-PROCEDURE.md), [document standard](docs/DOCUMENT-STANDARD.md) and [setup acceptance checklist](docs/ACCEPTANCE.md).

## Contributing to this template

Use fictional data in examples and tests. Run the standard-library test suite and validation before a PR. Do not submit your company's populated brain, configuration secrets or private URLs upstream. Changes to record formats need migration instructions. [CONTRIBUTING.md](CONTRIBUTING.md) describes the development workflow.
