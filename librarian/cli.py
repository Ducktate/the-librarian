"""Structured local readers, intake drafts and evidence reports (Python 3.11+)."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import contracts, knowledge as k

SCOPE = 'Local brain files only; evidence assertions are unverified. No source truth, runtime freshness, publication authority or scheduler verification is implied.'


class UsageError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=15)
    return result.stdout.strip() if result.returncode == 0 else None


def revision(root):
    status = git(root, 'status', '--porcelain', '--', 'wiki', 'inbox', 'receipts', 'librarian.json')
    return {'commit': git(root, 'rev-parse', 'HEAD'),
            'dirty': bool(status) if status is not None else None,
            'scope': 'Local brain checkout; excludes verification of original source repositories.'}


def page_row(root, pid, item):
    path, meta, _ = item
    return {'id': pid, 'path': path.relative_to(root).as_posix(), 'title': meta['title'],
            'status': meta['status'], 'owner': meta['owner'], 'last_verified': meta['last_verified'],
            'verified_scope': meta['verified_scope'], 'content_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read(root, pid, offset=0, limit=100):
    pages = k.page_map(root)
    if pid not in pages:
        raise ValueError(f'unknown exact page ID: {pid}')
    path, _, body = pages[pid]
    # Body lines, zero-based offset. Hash covers the entire exact file including frontmatter.
    lines = body.splitlines()
    return {**page_row(root, pid, pages[pid]), 'revision': revision(root), 'offset': offset,
            'limit': limit, 'total_lines': len(lines), 'next_offset': offset + limit if offset + limit < len(lines) else None,
            'body': '\n'.join(lines[offset:offset + limit])}


def query(root, text, offset=0, limit=20):
    terms = text.lower().split()
    rows = []
    for pid, item in k.page_map(root).items():
        haystack = (item[1]['title'] + ' ' + item[2]).lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            rows.append({**page_row(root, pid, item), 'score': score})
    rows.sort(key=lambda row: (-row['score'], row['id']))
    return {'results': rows[offset:offset + limit], 'offset': offset, 'limit': limit,
            'total': len(rows), 'next_offset': offset + limit if offset + limit < len(rows) else None,
            'revision': revision(root)}


def source_check(event, checkout):
    """Verify Git revisions and exact changed filenames, never read source bodies."""
    context = event['context']
    errors = []
    base, change = context.get('base_revision'), context.get('change_revision')
    for name, rev in [('base_revision', base), ('change_revision', change)]:
        if not isinstance(rev, str) or not re.fullmatch(r'[0-9a-f]{40}', rev) or git(checkout, 'rev-parse', '--verify', rev + '^{commit}') != rev:
            errors.append(f'{name}: exact source Git commit unavailable')
    if errors:
        return errors
    filenames = git(checkout, 'diff', '--name-only', '--no-renames', base, change, '--')
    if filenames is None:
        return ['cannot inspect changed filenames between exact source revisions']
    changed = set(filenames.splitlines())
    selected = [entry['path'] for row in event.get('changes', [])
                if row['repository'] == context.get('repository') for entry in row['paths']]
    if not selected:
        errors.append('source-checkout requires changes matching context.repository')
    for path in selected:
        if path not in changed:
            errors.append(f'path is not changed between exact source revisions: {path}')
    return errors


def draft_update(root, args):
    value = k.read_json(root / 'templates/contribution.json')
    value.update(event_id=str(uuid.uuid4()), observed_at=None, draft=True)
    value['author'] = {name: getattr(args, name, None) for name in ('agent', 'session', 'machine')}
    value['affected_page_ids'] = args.page_id or []
    value['context']['repository'] = args.repository
    value['context']['base_revision'] = args.base_revision
    if args.source_checkout:
        checkout = args.source_checkout.resolve()
        head = git(checkout, 'rev-parse', 'HEAD')
        if head is None:
            raise ValueError('source checkout has no readable Git HEAD')
        value['context']['change_revision'] = head
        base = args.base_revision
        if base is not None:
            if not re.fullmatch(r'[0-9a-f]{40}', base) or git(checkout, 'rev-parse', '--verify', base + '^{commit}') != base:
                raise ValueError('base_revision must be an available full source commit')
            paths = (git(checkout, 'diff', '--name-only', '--no-renames', base, head, '--') or '').splitlines()
            value['changes'] = [{'repository': args.repository, 'module': args.module,
                'paths': [{'path': path, 'before': None, 'after': None, 'reason': None, 'evidence': []} for path in paths],
                'commits': [head], 'pull_requests': []}]
    return value


def draft_receipt(root, args):
    event_set = k.events(root)
    if args.event_id not in event_set:
        raise ValueError('receipt draft requires an existing event ID')
    value = k.read_json(root / 'templates/receipt.json')
    value.update(event_id=args.event_id, sequence=len(k.history(root, args.event_id)) + 1,
                 run_id=args.run_id or str(uuid.uuid4()), status=args.status, draft=True)
    value['operator'] = {name: getattr(args, name, None) for name in ('agent', 'session', 'machine')}
    value['actor'] = args.agent
    return value


def lint_record(root, kind, value, source_checkout=None):
    if kind == 'contribution':
        errors = k.verify_event(root, value)
        if not errors and source_checkout:
            errors.extend(source_check(value, source_checkout))
        return errors
    errors = k.schema_errors(root, 'receipt', value)
    if errors:
        return errors
    previous = k.history(root, value['event_id'])
    if value.get('sequence', 0) <= len(previous):
        index = value['sequence'] - 1
        return [] if index >= 0 and previous[index] == value else ['immutable receipt conflict']
    return k.receipt_errors(root, value, previous, k.events(root))


def audit(root, base=None):
    errors = k.validate(root, base)
    records = []
    review_due = []
    review_date = datetime.now(timezone.utc).date()
    try:
        for pid, (_, meta, _) in k.page_map(root).items():
            verified = meta['last_verified']
            if verified is None or (meta['review_every_days'] > 0 and
                    (review_date - date.fromisoformat(verified)).days > meta['review_every_days']):
                review_due.append({'page_id': pid, 'last_verified': verified,
                                   'review_every_days': meta['review_every_days'],
                                   'basis': 'Declared page metadata only; no source freshness check.'})
        event_set = k.events(root)
        for eid, event in event_set.items():
            history = k.history(root, eid)
            latest = history[-1] if history else {}
            if event['schema_version'] == 1:
                records.append({'event_id': eid, 'flag': 'legacy_contract', 'detail': 'v1 retained unchanged; v2 details unavailable'})
            if latest.get('status') in k.FLAGS:
                records.append({'event_id': eid, 'flag': latest['status'], 'owner': latest['follow_up_owner'],
                                'question': latest['question'], 'required_evidence': latest['required_evidence'],
                                'follow_up_on': latest['follow_up_on']})
            if not history:
                records.append({'event_id': eid, 'flag': 'pending', 'detail': 'No librarian receipt'})
    except (OSError, ValueError, KeyError) as exc:
        if str(exc) not in errors:
            errors.append(str(exc))
    return {'valid': not errors, 'errors': errors, 'flags': records, 'revision': revision(root),
            'metadata_review_due': review_due, 'review_date_utc': review_date.isoformat(),
            'immutable_history_checked': base is not None, 'immutable_base': base,
            'limitations': ['Without --base, prior committed byte immutability is not compared.', SCOPE]}


def health(root):
    report = audit(root)
    cfg = k.read_json(root / 'librarian.json')
    public = contracts.public_remote(root)
    return {'mode': cfg.get('mode'), 'read_ready': report['valid'],
            'contribute_ready': report['valid'] and cfg.get('mode') == 'company' and not public,
            'public_remote': public, 'schedule_status': cfg.get('schedule', {}).get('status', 'not-configured'),
            'schedule_verified': False, 'runner_configured': bool(cfg.get('runner', {}).get('command')),
            'metadata_review_due': report['metadata_review_due'],
            'errors': report['errors'], 'revision': report['revision']}


def daily(root, day, zone, as_of):
    try:
        tz = ZoneInfo(zone)
    except ZoneInfoNotFoundError:
        raise ValueError('IANA timezone unavailable; install system timezone data (Windows may require tzdata)') from None
    target = date.fromisoformat(day)
    if target.isoformat() != day:
        raise ValueError('report date must be YYYY-MM-DD')
    start = datetime.combine(target, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(target + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    cutoff = contracts.timestamp(as_of) if as_of else datetime.now(timezone.utc)
    k.require_valid(k.validate(root))
    changes, audit_rows, sessions, flags = [], [], [], []
    event_set = k.events(root)
    for eid, event in event_set.items():
        observed = contracts.timestamp(event['observed_at'])
        if observed > cutoff:
            continue
        available = [receipt for receipt in k.history(root, eid) if contracts.timestamp(receipt['recorded_at']) <= cutoff]
        latest = available[-1] if available else {}
        if latest.get('status') in k.FLAGS:
            flags.append({'event_id': eid, **latest})
        today = [receipt for receipt in available if start <= contracts.timestamp(receipt['recorded_at']) < end]
        observed_today = start <= observed < end
        if not observed_today and not today:
            continue
        v2 = event.get('schema_version') == 2
        summary = event.get('summary') or {'headline': event['proposed_change'], 'why': None, 'impact': None}
        row = {'event_id': eid, 'observed_at': event['observed_at'], 'observed_today': observed_today,
                        'filed_today': any(r['status'] == 'filed' for r in today), 'summary': summary,
                        'kind': event['kind'], 'status_as_of': latest.get('status', 'pending'),
                        'delivery': event.get('delivery', {'state': 'unknown', 'evidence': []}),
                        'decision': event.get('decision', {'state': 'unknown', 'authority': None, 'evidence': []}),
                        'verification': event.get('verification'), 'author': event['author'],
                        'context': event['context'], 'changes': event.get('changes', []),
                        'sources': event['sources'], 'legacy_contract': not v2}
        if observed_today or any(r['status'] in {'filed', 'published'} for r in today):
            changes.append(row)
        sessions.append({'role': 'contributor', 'event_id': eid, **event['author']})
        for receipt in today:
            audit_rows.append({'event_id': eid, **receipt})
            sessions.append({'role': 'librarian_operator', 'event_id': eid,
                             **receipt.get('operator', {'agent': receipt['actor'], 'session': None, 'machine': None}),
                             'run_id': receipt.get('run_id')})
    return {'date': day, 'timezone': zone, 'as_of': cutoff.isoformat(),
            'window': {'start_utc': start.isoformat(), 'end_utc_exclusive': end.isoformat()},
            'executive_changes': sorted(changes, key=lambda row: (row['observed_at'], row['event_id'])),
            'audit': sorted(audit_rows, key=lambda row: (row['recorded_at'], row['event_id'], row['sequence'])),
            'flags': flags, 'sessions': sessions,
            'revision': revision(root), 'limitations': [SCOPE, 'Delivery and accepted decisions are contributor assertions with cited evidence, not independently verified authority.',
                'The report is an as-of view of immutable intake timestamps; wiki pages and Git revision describe the current checkout, not a historical reconstruction.']}


def markdown(report):
    lines = [f'# Daily evidence report: {report["date"]}', '', f'Timezone: {report["timezone"]}. As of: {report["as_of"]}.', '',
             f'UTC window: {report["window"]["start_utc"]} to {report["window"]["end_utc_exclusive"]} (exclusive).', '',
             f'Local brain revision: {report["revision"]["commit"] or "unavailable"}; dirty: {report["revision"]["dirty"]}.', '', '## Executive changes', '']
    for row in report['executive_changes']:
        summary = row['summary']
        lines += [f'- {summary["headline"]} ({row["event_id"]})', f'  Why: {summary["why"] or "unknown (legacy)"}',
                  f'  Impact: {summary["impact"] or "unknown (legacy)"}',
                  f'  Delivery assertion: {row["delivery"]["state"]}; decision assertion: {row["decision"]["state"]}; receipt status: {row["status_as_of"]}.',
                  f'  Observed today: {row["observed_today"]}; filed today: {row["filed_today"]}.',
                  '  Evidence: ' + ', '.join(row['sources'])]
        if row['verification']:
            lines += [f'  Verification assertion: {row["verification"]["result"]}.']
        for change in row['changes']:
            lines += [f'  Repository: {change["repository"]}; module: {change["module"]}; commits: {", ".join(change["commits"])}; PRs: {", ".join(change["pull_requests"])}.']
            for path in change['paths']:
                lines += [f'  Path: {path["path"]}; before: {path["before"]}; after: {path["after"]}; reason: {path["reason"]}.']
    if not report['executive_changes']:
        lines += ['No events observed or filed/published in this window.']
    lines += ['', '## Audit receipts and flags', '']
    for row in report['audit']:
        lines += [f'- {row["event_id"]} receipt {row["sequence"]}: {row["status"]} at {row["recorded_at"]}; {row["reason"]}']
        if row['status'] in k.FLAGS:
            lines += [f'  Owner: {row["follow_up_owner"]}; question: {row["question"]}; evidence needed: {row["required_evidence"]}; follow-up: {row["follow_up_on"]}.']
    lines += ['', '## Unresolved flags as of cutoff', '']
    for row in report['flags']:
        lines += [f'- {row["event_id"]}: {row["status"]}; owner: {row["follow_up_owner"]}; question: {row["question"]}; evidence: {row["required_evidence"]}; follow-up: {row["follow_up_on"]}.']
    lines += ['', '## Sessions', '']
    for row in report['sessions']:
        lines += [f'- {row["role"]}: agent={row["agent"]}; session={row["session"]}; machine={row["machine"]}; run={row.get("run_id", "not applicable")}.']
    lines += ['', '## Scope', ''] + ['- ' + item for item in report['limitations']]
    return '\n'.join(lines) + '\n'


def parser():
    p = Parser(description=__doc__)
    p.add_argument('--root', type=Path, default=k.ROOT)
    sub = p.add_subparsers(dest='command', required=True)
    # Legacy commands are dispatched by __main__; listed here for discoverability.
    sub.add_parser('configure', help='Configure a separate private company copy').add_argument('--company', required=True)
    sub.choices['configure'].add_argument('--owner', required=True)
    routine = sub.add_parser('routine', help='Run the existing bounded local adapter')
    routine.add_argument('--dry-run', action='store_true')
    routine.add_argument('--force', action='store_true')
    sub.add_parser('validate', help='Legacy whole-brain validation').add_argument('--base')
    sub.add_parser('queue', help='Legacy pending intake queue')
    sub.add_parser('search', help='Legacy bounded text search').add_argument('query')
    sub.add_parser('submit', help='Legacy immutable contribution intake').add_argument('file', type=Path)
    for name in ('query', 'read'):
        cmd = sub.add_parser(name)
        cmd.add_argument('query' if name == 'query' else 'page_id')
        cmd.add_argument('--offset', type=int, default=0)
        cmd.add_argument('--limit', type=int, default=20 if name == 'query' else 100)
    sub.add_parser('map')
    for name in ('audit', 'lint'):
        sub.add_parser(name).add_argument('--base')
    sub.add_parser('health')
    update = sub.add_parser('update').add_subparsers(dest='action', required=True)
    draft = update.add_parser('draft')
    draft.add_argument('--source-checkout', type=Path)
    draft.add_argument('--repository')
    draft.add_argument('--module')
    draft.add_argument('--base-revision')
    draft.add_argument('--page-id', action='append')
    draft.add_argument('--output', type=Path)
    for name in ('agent', 'session', 'machine'):
        draft.add_argument('--' + name)
    for name in ('lint', 'submit'):
        cmd = update.add_parser(name)
        cmd.add_argument('file', type=Path)
        cmd.add_argument('--source-checkout', type=Path)
    receipt = sub.add_parser('receipt').add_subparsers(dest='action', required=True)
    draft = receipt.add_parser('draft')
    draft.add_argument('--event-id', required=True)
    draft.add_argument('--status', choices=sorted(k.STATES), default='needs_context')
    draft.add_argument('--run-id')
    draft.add_argument('--output', type=Path)
    for name in ('agent', 'session', 'machine'):
        draft.add_argument('--' + name)
    cmd = receipt.add_parser('record')
    cmd.add_argument('file', type=Path)
    report = sub.add_parser('report').add_subparsers(dest='action', required=True).add_parser('daily')
    report.add_argument('--date', required=True)
    report.add_argument('--timezone', required=True)
    report.add_argument('--as-of')
    report.add_argument('--format', choices=['json', 'markdown'], default='json')
    report.add_argument('--output', type=Path)
    return p


def normalize_root(argv):
    """Allow the single global --root before or after any command."""
    argv = list(argv)
    roots = []
    rest = []
    i = 0
    while i < len(argv):
        value = argv[i]
        if value == '--root':
            if i + 1 >= len(argv):
                raise UsageError('--root requires a path')
            roots += ['--root', argv[i + 1]]
            i += 2
        elif value.startswith('--root='):
            roots += [value]
            i += 1
        else:
            rest.append(value)
            i += 1
    if len(roots) > 2:
        raise UsageError('specify --root once')
    return roots + rest


def output_file(root, path, text):
    path = path.resolve()
    # Reports/drafts must not overwrite tracked brain history or other files.
    for name in ('wiki', 'inbox', 'receipts', 'raw'):
        if path.is_relative_to((root / name).resolve()):
            raise ValueError('draft/report output cannot write into brain evidence or page directories')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def main(argv):
    command = ' '.join(argv[:2])
    try:
        args = parser().parse_args(normalize_root(argv))
        root = args.root.resolve()
        command = args.command + ((' ' + args.action) if hasattr(args, 'action') else '')
        errors = []
        if hasattr(args, 'offset') and (args.offset < 0 or not 1 <= args.limit <= 1000):
            raise UsageError('offset must be nonnegative and limit must be 1..1000')
        if args.command == 'query':
            data = query(root, args.query, args.offset, args.limit)
        elif args.command == 'read':
            data = read(root, args.page_id, args.offset, args.limit)
        elif args.command == 'map':
            data = {'pages': [page_row(root, pid, item) for pid, item in k.page_map(root).items()], 'revision': revision(root)}
        elif args.command in {'audit', 'lint'}:
            data = audit(root, args.base)
            errors = data['errors']
        elif args.command == 'health':
            data = health(root)
            errors = data['errors']
        elif args.command in {'update', 'receipt'}:
            if args.action == 'draft':
                data = draft_update(root, args) if args.command == 'update' else draft_receipt(root, args)
                if args.output:
                    output_file(root, args.output, json.dumps(data, indent=2) + '\n')
            else:
                value = k.read_json(args.file)
                kind = 'contribution' if args.command == 'update' else 'receipt'
                errors = lint_record(root, kind, value, getattr(args, 'source_checkout', None))
                if not errors and args.action in {'submit', 'record'} and value.get('schema_version') != 2:
                    if kind == 'contribution':
                        exact_retry = k.events(root).get(value.get('event_id')) == value
                    else:
                        exact_retry = value in k.history(root, value.get('event_id', ''))
                    if not exact_retry:
                        errors.append('new CLI records require schema_version 2; v1 is historical read/exact-retry only')
                data = {'valid': not errors}
                if not errors and args.action in {'submit', 'record'}:
                    path, state = (k.submit if kind == 'contribution' else k.append_receipt)(root, value)
                    data = {'path': path.relative_to(root).as_posix(), 'status': state, 'local_only': True}
        elif args.command == 'report':
            data = daily(root, args.date, args.timezone, args.as_of)
            content = markdown(data) if args.format == 'markdown' else json.dumps({'ok': True, 'command': command, 'data': data, 'errors': [], 'scope': SCOPE}, indent=2) + '\n'
            if args.output:
                output_file(root, args.output, content)
            elif args.format == 'markdown':
                print(content, end='')
                return 0
        print(json.dumps({'ok': not errors, 'command': command, 'data': data, 'errors': errors, 'scope': SCOPE}, indent=2))
        return 2 if errors else 0
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'command': command, 'data': None, 'errors': [str(exc)], 'scope': SCOPE}))
        return 2
    except (OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'ok': False, 'command': command, 'data': None, 'errors': [str(exc)], 'scope': SCOPE}))
        return 3
