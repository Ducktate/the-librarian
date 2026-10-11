# CLI and audit contracts

Run commands in your private brain, or set --root PATH once before or after a command.
Python 3.11+ and Git are required. New commands return JSON envelopes with ok, command,
data, errors and scope. Exit codes are 0 success, 2 input/validation failure and 3 runtime
failure. Markdown report output is plain Markdown. Legacy commands retain their original
output/exit behavior; inspect --help for the installed version.

## Predictable reading

```sh
python -m librarian query "hosting" --offset 0 --limit 5
python -m librarian read brain-index --offset 0 --limit 40
python -m librarian map
```

Query ranks local title/body keyword matches and returns page metadata, file hashes and
pagination, not an answer verified against sources. Read requires an exact stable page ID;
offset is a zero-based body-line offset, excluding frontmatter. Limit is 1..1000. Follow
next_offset only when needed. Map lists page metadata, not a graph engine or a proof of
complete company coverage. Record checkout revision, dirty state and retrieval time.
Inspect original evidence before using a claim. No command here fetches remote sources.

## Draft and submit an update

Flags in this example are placeholders. Replace paths/labels/identities with actual values;
BASE_FULL_SHA is an available full 40-character source commit, not literal text.

```sh
python -m librarian update draft --source-checkout SOURCE_PATH --repository REPOSITORY --module MODULE --base-revision BASE_FULL_SHA --page-id brain-index --agent AGENT --session SESSION --machine MACHINE --output update-draft.json
python -m librarian update lint update-draft.json --source-checkout SOURCE_PATH
python -m librarian update submit update-draft.json --source-checkout SOURCE_PATH
```

--page-id repeats. --source-checkout, --repository, --module, --base-revision and identity
flags are optional for generation; missing required record values must be filled later.
Without --output the draft is inside the JSON envelope's data field; save data, not the
whole envelope, as the record. Output paths must be new files and cannot be inside the
brain's wiki/inbox/receipts/raw directories.

Draft generation creates a UUID and marks draft=true. With --source-checkout and an
explicit base revision it reads Git HEAD and changed filenames; it does not write claims,
before/after behavior, reasons, test proof or actual session identity for you. Inspect the
diff yourself, fill the record from evidence and set draft=false. A generated draft is
deliberately invalid for submission until completed. Do not make it pass by inventing proof.

V2 extends the original event fields with:

| Field | Required evidence |
| --- | --- |
| summary | headline, why and impact: useful explanation of what changed |
| author | Actual agent, session and machine, not placeholders |
| context | Distinct full base_revision/change_revision; source repository and actual commit/issue/PR fields as applicable |
| changes | Per repository/module: exact paths with before, after, reason and evidence; actual commits or PRs |
| verification | result (not_run, passed, failed, unknown) and evidence; passed/failed require proof |
| delivery | state and typed evidence appropriate to implemented/tested/merged/deployed/client_qualified |
| decision | none/proposed/accepted/rejected; accepted requires named authority and approval evidence |
| draft | false only after the record is completed |

Keep claims, sources, affected_page_ids, proposed_change, questions and other original
fields required by schemas/contribution-v2.schema.json. Exact paths are canonical relative
POSIX paths: no backslashes, wildcard, absolute path or traversal. Sources are HTTPS
references or canonical local brain evidence paths. Path/verification/delivery/decision
references must appear in sources. Each repository/module change needs commits or PRs.
Use real source-revision and evidence-path information even for a non-code decision record;
this contract is not a free-form note format.

Delivery evidence objects contain type, source and detail. Matching types are source_code
for implemented, test for tested, merge for merged, deployment for deployed and
client_acceptance for client_qualified. A source-code citation cannot prove deployment.
Each claim's delivery_state must match the typed delivery state. Decision evidence uses
proposal, owner_approval, authority_decision or rejection. Accepted decisions require
owner_approval or authority_decision plus decision.authority and decision_authority.
Use kind=proposal until actual authority accepts a decision.

Lint validates the completed record against the brain. --source-checkout additionally
verifies available exact base/change commits and that recorded paths for context.repository
changed between them. It reads Git filenames, not source bodies. It does not validate path
behavior, another repository, full diff coverage, tests, merge, deployment or authority.
Use that flag for code changes and disclose its limited verification scope.

Submit stores inbox/YYYY/MM/UUID.json by the UTC observed_at month. It is local-only:
sharing requires the private repository's authorized workflow. Identical retries are
idempotent. Changed content under an existing ID is rejected; corrections use a new event
ID with supersedes_event_id. Do not edit immutable intake to repair an error.

## Record librarian outcomes

```sh
python -m librarian receipt draft --event-id EVENT_UUID --status needs_context --agent OPERATOR --session SESSION --machine MACHINE --run-id RUN_UUID --output receipt-draft.json
python -m librarian receipt record receipt-draft.json
```

The event must already exist. --run-id is optional at generation (a UUID is generated);
use the actual run UUID consistently across that run. operator records the real agent,
session and machine; actor must match operator.agent. The draft supplies next sequence.
Complete recorded_at, reason, verification_notes and outcome fields, then set draft=false.
Record requires the explicit correct sequence and appends receipts/EVENT_ID/NNNN.json.
Never reuse fabricated operator/session values. Receipt timing cannot precede its event
or previous receipt.

Flags (needs_context, disputed, authority_required, blocked_access) need follow_up_owner,
question, required_evidence and follow_up_on. Filed/published need exact affected paths.
Published requires prior filed and a full published_commit; the operator must independently
verify authorized main-branch content. Duplicate requires the related event. Terminal
published/duplicate/rejected outcomes are immutable; use correction events thereafter.
Exact retries return the existing record.

## Audit, lint and health

```sh
python -m librarian audit --base origin/main
python -m librarian lint --base origin/main
python -m librarian health
```

Audit/lint validate page metadata, local references, events and receipt histories and expose
pending events, flags, metadata review dates and legacy-contract gaps. metadata_review_due
uses declared page dates/intervals, not a source freshness check; audit records review_date_utc.
--base compares committed immutable records
against that Git revision; without it past byte immutability is not checked. Neither command
verifies original source truth, confidentiality, owner authority or scheduler operation.

Health reports structural local readiness, mode, public-remote guard, runner configuration
and recorded schedule status. schedule_verified remains false: actual schedule/first-run
proof belongs to the configured environment and automation register. A valid template's
read_ready flag does not prove a requested agent connected or any company fact verified.

## Daily executive and audit report

```sh
python -m librarian report daily --date 2030-04-12 --timezone UTC --as-of 2030-04-13T00:00:00Z --format json --output daily-report.json
python -m librarian report daily --date 2030-04-12 --timezone UTC --as-of 2030-04-13T00:00:00Z --format markdown --output daily-report.md
```

Dates are fictional. --date is the chosen local calendar date; --timezone is an IANA name.
The local-midnight window is converted to UTC and end-exclusive, respecting timezone data.
Windows may need installed timezone data (the CLI uses standard-library zoneinfo).
--as-of is an explicit timestamp with offset; if omitted it uses the current UTC time.
Supply it for reproducible reporting. --format is json or markdown; --output writes a new
file. Otherwise JSON/Markdown is printed. Reports do not overwrite files or record history.

The artifact separates executive_changes from detailed audit receipts/flags and sessions.
The executive view includes events observed in the day or earlier events filed/published
that day; audit includes that day's receipts. Flags reflect unresolved state at the cutoff.
Future events/receipts are excluded. Retain these views separately when distributing a
summary; the CLI produces one structured artifact, not separate delivery channels.
Extract the executive summary for separate authorized distribution and retain the full
audit privately. For opted-in daily reports, use routine --force or a separate report job
so an empty intake queue does not skip reporting.

Report metadata includes date, timezone, as_of, UTC window, revision and limitations.
Contributor identities remain distinct from librarian operator/session/run attribution.
Legacy v1 details appear unknown rather than invented. Delivery/decisions are evidence-backed
assertions, not independent proof. Records are viewed as-of; wiki pages and Git revision
describe the current checkout, not a historical reconstruction. No report means all source
repositories, features or releases were inspected. No notifications are sent by this CLI.
Daily executive notifications are opt-in and require the user's authorized destination.

## Compatibility and configuration

Historical contribution.schema.json and receipt.schema.json remain v1; new records use
contribution-v2.schema.json and receipt-v2.schema.json. Page frontmatter remains v1.
Read/audit/report accept mixed historical records. New submit/record rejects v1 except
an exact already-stored retry. Do not rewrite history during migration. Add missing knowledge
with a new v2 correction/superseding event and real operator-attributed receipts.

Legacy validate, queue, search, submit FILE and receipt FILE aliases remain available.
They are compatibility entrypoints, not permission to create new v1 records. Configure and
routine remain available with their documented behavior. Public upstream remotes guard
company configuration and record mutation: create your own private copy and remove the
public remote before populating. The runtime wrapper invokes an explicitly configured
installed adapter; it does not include a model, credentials, scheduler or automatic merge.
See SCHEDULING.md and ACCEPTANCE.md for actual readiness proof.
