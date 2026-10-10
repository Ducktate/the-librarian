# Document and frontmatter standard

Every maintained page under wiki/ starts with YAML frontmatter between `---` lines. V1 uses one `key: JSON-value` per line so Python's standard library can read a strict, portable YAML subset. Quote strings and dates; write arrays inline. Multiline YAML values, tags and anchors are not supported. Use templates/page.md.

Required fields: schema_version, id, title, type, domain, owner, maintainer, status, confidentiality, sources, last_verified, verified_scope, review_every_days, review_trigger, related_ids, supersedes, superseded_by. The JSON schemas define allowed values. IDs are stable lowercase identifiers and must not be reused. Owners are real accountable identities in your ownership page; unassigned is an explicit gap.

Use draft for proposals, active for adopted/verified records, needs_context for gaps, disputed for conflicting claims, deprecated for replaced guidance and archived for historical material. Document state is separate from a capability's delivery state. Do not activate a page just because it parses.

The body starts with the useful answer and includes a home/parent link, scope, facts, evidence near claims, limitations, owner questions and related records. Keep detailed contracts in their original repositories and cite immutable commit links. A source URL alone does not prove you read or verified it.

last_verified is the date of a real check; null means never verified. verified_scope says exactly what was checked and what was not. If only one row was checked, retain dates on the others. review_trigger covers relevant deployments, contract changes, decisions and new invoices. Review periods are maximums; historical decision pages alone may use 0.

Store necessary sanitized evidence under raw/ with source, acquisition time, revision/environment and scope. Events and receipts are separate typed records, not wiki pages. README, instructions, templates and examples have their own formats and are not maintained company-fact pages.

A decision page names decision maker, authority evidence, effective date, alternatives, rationale, consequences, affected surfaces and reversal trigger. Proposals remain proposals. Supersession links must be reciprocal. Moving a page preserves its ID and updates all links.

Run `python -m librarian validate`. It checks metadata, IDs, local references and record histories. `--base origin/main` also detects edits/deletions of committed evidence and records. It does not verify remote links, truth, confidentiality or authority; those need the librarian/reviewer.
