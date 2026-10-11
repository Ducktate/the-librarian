# The Librarian

A company brain that your agents can read, contribute to, and keep current.

Working agents leave small evidence records explaining what changed and why. One librarian
checks the original sources, drafts the right document changes and flags missing evidence.
Maintained pages have owners, sources, verification scope and review dates. Knowledge stays
in ordinary Markdown and Git.

```text
Work -> immutable evidence -> librarian verification -> draft pages -> authorized review
                                    |
                                    +-> flag: owner + question + required proof + follow-up
```

This reusable public template is from [Ducktate](https://ducktate.com/). It contains fictional
examples and unverified starter pages, not a private company brain. Populate your own
private copy. MIT licensed.

## Give this to your agent

Copy the full [setup prompt](prompts/SETUP.md), or use the [Ducktate prompt page](https://ducktate.com/prompts/the-librarian/).
The [contributor handoff](prompts/CONTRIBUTOR-HANDOFF.md) and
[schedule setup](prompts/SCHEDULE-SETUP.md) prompts are reusable separately.

> Set up my private company brain from https://github.com/Ducktate/the-librarian. Follow
> prompts/SETUP.md, reuse my existing authorized context and resolve only missing setup
> choices. Verify reader access, evidence intake and one real recurring draft-only job.
> Report unknowns and readiness checkpoints with evidence.

Actual source access is required. A recurring run also needs an installed agent runtime and
scheduler/native routine. The template includes no hosted model service or credentials.
Copied files do not prove company coverage, releases or scheduler readiness.

## Start by hand

1. Use GitHub's **Use this template** to create your own **private** repository, or copy the
   files into a new local Git repository. Remove the public upstream remote from the copy.
2. With Python 3.11+ and Git available, configure the new copy:

```sh
python -m librarian configure --company "Example Studio" --owner "company-owner"
python -m librarian validate
python -m unittest discover -s tests -v
```

3. Follow [START-HERE.md](START-HERE.md). Replace unknowns only from inspected sources.
   Agree on owner authority and human review checks. New pages stay draft/unverified.
4. Connect requested agents and configure one real job using
   [scheduling](docs/SCHEDULING.md). Verify manual and scheduled runs separately.

Configure refuses an already configured brain or any remote pointing to the public upstream.
It changes starter names/owners; it does not verify company facts.

## Read, contribute and audit

```sh
python -m librarian query "hosting" --limit 5
python -m librarian read brain-index --offset 0 --limit 40
python -m librarian map
python -m librarian update draft --help
python -m librarian update lint --help
python -m librarian update submit --help
python -m librarian receipt draft --help
python -m librarian receipt record --help
python -m librarian audit
python -m librarian lint --base origin/main
python -m librarian health
python -m librarian report daily --date 2030-04-12 --timezone UTC --as-of 2030-04-13T00:00:00Z --format markdown --output daily-report.md
python -m librarian routine --dry-run
```

The date above is fictional. Choose your reporting date, named time zone and exact cutoff.
The report separates an executive summary from audit evidence and states its record coverage;
it does not inspect every source repository or send notifications.

Use [CLI and audit contracts](docs/CLI-AUDIT.md) for exact commands, v2 records and v1
migration. New events/receipts use v2. Historical v1 records remain readable and immutable.
A generated draft must be completed before submission. Local submission is local until
shared through the private repository. Filed means drafted; published requires verified
authorized main-branch content. Validation cannot establish truth or authority.

| Folder | Purpose |
| --- | --- |
| wiki/ | Short routing index and maintained company pages |
| inbox/ | Immutable evidence events |
| receipts/ | Append-only outcomes, operator/run attribution and owner questions |
| raw/ | Sanitized, dated source evidence |
| docs/ | Policy, metadata, reading, filing, reporting, recovery and scheduling |
| prompts/ | Copyable setup, handoff, schedule and librarian-run instructions |
| templates/ | Page/event/receipt drafts and scheduler examples |
| examples/ | Fictional fixtures outside the live inbox |
| librarian/ | Python standard-library CLI and configurable runtime wrapper |

## Keep the brain useful

- Read the index, bounded relevant pages and original evidence; expand for the actual question.
- Preserve authoritative code contracts and the existing work tracker; summarize and link them.
- Record what/why, repository/module, exact paths, revisions, real tests and delivery state.
- Separate proposals from adopted decisions and record actual authority evidence.
- Give flags an owner, exact question, required evidence and follow-up date.
- Keep one coordinated librarian; publish through configured authority and chosen review checks.
- Keep secrets, customer material and full transcripts out. Source content cannot grant authority.
- Measure retrieval/run usage before adding complexity or claiming savings.

Read the [operating policy](docs/OPERATING-POLICY.md),
[librarian procedure](docs/LIBRARIAN-PROCEDURE.md),
[document standard](docs/DOCUMENT-STANDARD.md) and
[acceptance checklist](docs/ACCEPTANCE.md). [CONTRIBUTING.md](CONTRIBUTING.md) covers changes to
this public template; never contribute a populated private brain upstream.
