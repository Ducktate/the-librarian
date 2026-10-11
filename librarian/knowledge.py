"""Portable company-brain files, validation, search and append-only local intake.

No network calls, implicit publication, credentials or third-party dependencies.
Schemas use the explicitly supported JSON Schema subset in check_schema().
"""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from . import contracts

ROOT = Path(__file__).resolve().parent.parent
FLAGS = {'needs_context', 'disputed', 'authority_required', 'blocked_access'}
TERMINAL = {'published', 'duplicate', 'rejected'}
STATES = FLAGS | TERMINAL | {'filed'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def parse_page(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        raise ValueError('missing frontmatter')
    try:
        end = lines.index('---', 1)
    except ValueError:
        raise ValueError('unclosed frontmatter') from None
    meta = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(':')
        if not sep or not re.fullmatch(r'[a-z][a-z_]*', key) or key in meta:
            raise ValueError('invalid or duplicate frontmatter key')
        try:
            meta[key] = json.loads(value.strip())
        except ValueError:
            raise ValueError(f'{key}: expected one JSON-compatible YAML value') from None
    return meta, '\n'.join(lines[end + 1:])


def check_schema(value, schema, label='$'):
    """Validate the subset used by our checked-in schemas (no remote refs)."""
    errors = []
    if 'anyOf' in schema:
        if not any(not check_schema(value, option, label) for option in schema['anyOf']):
            return [f'{label}: does not match any allowed type/shape']
        return []
    types = {'object': dict, 'array': list, 'string': str, 'integer': int,
             'null': type(None), 'boolean': bool}
    kind = schema.get('type')
    if kind and (not isinstance(value, types[kind]) or (kind == 'integer' and isinstance(value, bool))):
        return [f'{label}: expected {kind}']
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{label}: invalid choice')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        errors.append(f'{label}: expected {schema["const"]}')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{label}.{key}: required')
        props = schema.get('properties', {})
        for key, item in value.items():
            if key in props:
                errors.extend(check_schema(item, props[key], f'{label}.{key}'))
            elif schema.get('additionalProperties') is False:
                errors.append(f'{label}.{key}: unexpected field')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            errors.append(f'{label}: too few items')
        if schema.get('uniqueItems') and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append(f'{label}: duplicate items')
        for i, item in enumerate(value):
            errors.extend(check_schema(item, schema.get('items', {}), f'{label}[{i}]'))
    if isinstance(value, str):
        if len(value.strip()) < schema.get('minLength', 0):
            errors.append(f'{label}: empty value')
        if schema.get('pattern') and not re.search(schema['pattern'], value):
            errors.append(f'{label}: invalid format')
        try:
            if schema.get('format') == 'date':
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            if schema.get('format') == 'date-time':
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if parsed.tzinfo is None or 'T' not in value:
                    raise ValueError()
        except ValueError:
            errors.append(f'{label}: invalid {schema["format"]}')
    if isinstance(value, int) and value < schema.get('minimum', value):
        errors.append(f'{label}: below minimum')
    return errors


def schema_errors(root, kind, value):
    version = value.get('schema_version') if isinstance(value, dict) else None
    suffix = '-v2' if kind in {'contribution', 'receipt'} and version == 2 else ''
    return check_schema(value, read_json(root / 'schemas' / f'{kind}{suffix}.schema.json'))


def require_valid(errors):
    if errors:
        raise ValueError('\n'.join(errors))


def local_ref(root, ref, base=None):
    """Sources are root-relative; Markdown links are relative to their page."""
    if ref.startswith('https://'):
        return None
    ref = ref.split('#', 1)[0]
    if not ref:
        return None
    target = ((base or root) / ref).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('reference escapes brain root')
    return target


def page_map(root):
    out = {}
    for path in sorted((root / 'wiki').rglob('*.md')):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('wiki file resolves outside brain root')
        meta, body = parse_page(path)
        require_valid(schema_errors(root, 'page', meta))
        if meta['id'] in out:
            raise ValueError(f'duplicate page ID: {meta["id"]}')
        out[meta['id']] = (path, meta, body)
    if not out:
        raise ValueError('no wiki pages')
    return out


def event_paths(root):
    return sorted((root / 'inbox').rglob('*.json'))


def events(root):
    out = {}
    for path in event_paths(root):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('event file resolves outside brain root')
        event = read_json(path)
        require_valid(schema_errors(root, 'contribution', event))
        eid = event['event_id']
        if eid in out:
            raise ValueError(f'duplicate event ID: {eid}')
        if path != event_destination(root, event):
            raise ValueError(f'event path/date mismatch: {path.relative_to(root)}')
        out[eid] = event
    return out


def event_destination(root, event):
    stamp = datetime.fromisoformat(event['observed_at'].replace('Z', '+00:00')).astimezone(timezone.utc)
    return root / 'inbox' / f'{stamp:%Y}' / f'{stamp:%m}' / f'{event["event_id"]}.json'


def verify_event(root, event, pages=None):
    errors = schema_errors(root, 'contribution', event)
    if errors:
        return errors
    errors.extend(contracts.event_errors(event))
    pages = pages or page_map(root)
    for pid in event['affected_page_ids']:
        if pid not in pages:
            errors.append(f'unknown affected page ID: {pid}; use brain-index for proposed new pages')
    for ref in event['sources']:
        try:
            path = local_ref(root, ref)
            if path and not path.is_file():
                errors.append(f'missing event source: {ref}')
        except ValueError as e:
            errors.append(str(e))
    for claim in event['claims']:
        if not set(claim['evidence']).issubset(event['sources']):
            errors.append('claim evidence must appear in event sources')
    if event['kind'] == 'decision' and not event['decision_authority']:
        errors.append('decision requires authority evidence; otherwise submit proposal')
    if event['kind'] == 'cost' and not event['cost_impact']:
        errors.append('cost event requires cost_impact')
    return errors


def history(root, eid):
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', eid):
        raise ValueError('invalid event ID')
    result = []
    for path in sorted((root / 'receipts' / eid).glob('*.json')):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('receipt file resolves outside brain root')
        result.append(read_json(path))
    return result


def receipt_errors(root, receipt, previous, event_set):
    errors = schema_errors(root, 'receipt', receipt)
    if errors:
        return errors
    state = receipt['status']
    if receipt['event_id'] not in event_set:
        errors.append('receipt refers to missing event')
    else:
        errors.extend(contracts.receipt_errors(receipt, previous, event_set[receipt['event_id']]))
    if receipt['sequence'] != len(previous) + 1:
        errors.append('receipt sequence must be contiguous')
    if previous and previous[-1]['status'] in TERMINAL:
        errors.append('terminal receipt cannot be changed; submit a correction event')
    if previous:
        current_time = datetime.fromisoformat(receipt['recorded_at'].replace('Z', '+00:00'))
        old_time = datetime.fromisoformat(previous[-1]['recorded_at'].replace('Z', '+00:00'))
        if current_time < old_time:
            errors.append('receipt timestamp precedes previous receipt')
    if state in FLAGS:
        for field in ('follow_up_owner', 'question', 'required_evidence', 'follow_up_on'):
            if not receipt[field]:
                errors.append(f'{state} requires {field}')
    if state in {'filed', 'published'} and not receipt['affected_paths']:
        errors.append(f'{state} requires affected_paths')
    if state == 'published':
        if not previous or previous[-1]['status'] != 'filed':
            errors.append('published requires previous filed receipt')
        if not receipt['published_commit']:
            errors.append('published requires full published_commit')
    elif receipt['published_commit'] is not None:
        errors.append('published_commit only allowed for published status')
    if state == 'duplicate' and not receipt['related_event_id']:
        errors.append('duplicate requires related_event_id')
    related = receipt['related_event_id']
    if related and (related not in event_set or related == receipt['event_id']):
        errors.append('related_event_id must reference a different existing event')
    for ref in receipt['affected_paths']:
        try:
            path = local_ref(root, ref)
            if not path or not path.is_file() or not ref.startswith('wiki/'):
                errors.append(f'affected path must be an existing wiki page: {ref}')
        except ValueError as e:
            errors.append(str(e))
    return errors


def immutable_changes(root, base):
    """Reject edits/removals of previously recorded evidence, events and receipts."""
    result = subprocess.run(['git', 'diff', '--name-status', '--no-renames', base, '--',
                             'inbox', 'receipts', 'raw'], cwd=root, capture_output=True,
                            text=True, timeout=15)
    if result.returncode:
        return ['cannot compare immutable history to requested Git base']
    errors = []
    for line in result.stdout.splitlines():
        status, _, path = line.partition('\t')
        if status != 'A' and (path.endswith('.json') or path.startswith('raw/')):
            errors.append(f'immutable history changed: {path}; add a correction record')
    return errors


def validate(root, base=None):
    errors = []
    if base:
        errors.extend(immutable_changes(root, base))
    try:
        pages = page_map(root)
        event_set = events(root)
    except (OSError, ValueError, KeyError) as e:
        return [str(e)]
    for pid, (path, meta, body) in pages.items():
        label = str(path.relative_to(root))
        for target in meta['related_ids'] + meta['supersedes'] + meta['superseded_by']:
            if target not in pages:
                errors.append(f'{label}: unknown related/supersession ID {target}')
        for field, opposite in [('supersedes', 'superseded_by'), ('superseded_by', 'supersedes')]:
            for target in meta[field]:
                if target in pages and pid not in pages[target][1][opposite]:
                    errors.append(f'{label}: supersession must be reciprocal with {target}')
        if meta['status'] == 'active' and (not meta['sources'] or meta['last_verified'] is None or meta['owner'] == 'unassigned'):
            errors.append(f'{label}: active page needs sources, verification date and owner')
        if meta['review_every_days'] == 0 and meta['type'] != 'decision':
            errors.append(f'{label}: only historical decisions may have no interval')
        refs = [(ref, root) for ref in meta['sources']]
        refs += [(ref, path.parent) for ref in re.findall(r'\]\(([^)\s]+)\)', body)]
        for ref, base in refs:
            try:
                target = local_ref(root, ref, base)
                if target and not target.is_file():
                    errors.append(f'{label}: missing reference {ref}')
            except ValueError as e:
                errors.append(f'{label}: {e}')
    for eid, event in event_set.items():
        errors.extend(f'{eid}: {e}' for e in verify_event(root, event, pages))
        related = event['supersedes_event_id']
        if related and (related not in event_set or related == eid):
            errors.append(f'{eid}: supersedes_event_id must name a different existing event')
    previous_by_event = {}
    for path in sorted((root / 'receipts').rglob('*.json')):
        try:
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('receipt file resolves outside brain root')
            receipt = read_json(path)
            require_valid(schema_errors(root, 'receipt', receipt))
            eid = receipt['event_id']
            prev = previous_by_event.setdefault(eid, [])
            expected = root / 'receipts' / eid / f'{receipt["sequence"]:04d}.json'
            if path != expected:
                errors.append(f'{path}: receipt filename mismatch')
            errors.extend(f'{path.relative_to(root)}: {e}' for e in receipt_errors(root, receipt, prev, event_set))
            prev.append(receipt)
        except (OSError, ValueError, KeyError) as e:
            errors.append(f'{path}: {e}')
    return errors


def store_immutable(path, value):
    """Publish completed bytes without overwriting another process's record.

    Hard-link publication is atomic on NTFS and normal POSIX filesystems. If
    unsupported, fail and keep input outside intake instead of exposing partial JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / ('.pending-' + str(uuid.uuid4()))
    try:
        with temp.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
            return 'stored'
        except FileExistsError:
            if read_json(path) == value:
                return 'unchanged'
            raise ValueError(f'immutable record conflict: {path.name}') from None
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def write_lock(root):
    """Serialize local intake checks and writes; Git still coordinates machines."""
    lock = root / '.brain-write.lock'
    try:
        stream = lock.open('x', encoding='utf-8')
    except FileExistsError:
        raise ValueError('brain write busy; inspect .brain-write.lock and retry. Remove a stale lock only after confirming its process has exited.') from None
    try:
        with stream:
            json.dump({'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()}, stream)
        yield
    finally:
        lock.unlink(missing_ok=True)


def submit(root, event):
    contracts.mutation_guard(root)
    with write_lock(root):
        return _submit(root, event)


def _submit(root, event):
    require_valid(validate(root))
    require_valid(verify_event(root, event))
    existing = events(root)
    eid = event['event_id']
    if eid in existing:
        if existing[eid] != event:
            raise ValueError('event ID already exists with different content')
        return event_destination(root, event), 'unchanged'
    related = event['supersedes_event_id']
    if related and related not in existing:
        raise ValueError('superseded event does not exist')
    path = event_destination(root, event)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('event destination resolves outside brain root')
    return path, store_immutable(path, event)


def append_receipt(root, receipt):
    contracts.mutation_guard(root)
    with write_lock(root):
        return _append_receipt(root, receipt)


def _append_receipt(root, receipt):
    require_valid(validate(root))
    receipt = dict(receipt)
    eid = receipt.get('event_id', '')
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', eid):
        raise ValueError('invalid event ID')
    previous = history(root, eid)
    # An explicit sequence identifies an exact immutable historical retry.
    if 'sequence' in receipt and isinstance(receipt['sequence'], int) and 1 <= receipt['sequence'] <= len(previous):
        old = previous[receipt['sequence'] - 1]
        if old == receipt:
            return root / 'receipts' / eid / f'{receipt["sequence"]:04d}.json', 'unchanged'
        raise ValueError('immutable receipt conflict: sequence already exists')
    # Retry a semantically identical last record without creating a new sequence.
    if previous and 'sequence' not in receipt and {k:v for k,v in previous[-1].items() if k != 'sequence'} == {k:v for k,v in receipt.items() if k != 'sequence'}:
        return root / 'receipts' / eid / f'{len(previous):04d}.json', 'unchanged'
    receipt.setdefault('sequence', len(previous) + 1)
    require_valid(receipt_errors(root, receipt, previous, events(root)))
    path = root / 'receipts' / eid / f'{receipt["sequence"]:04d}.json'
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('receipt destination resolves outside brain root')
    return path, store_immutable(path, receipt)


def queue(root):
    require_valid(validate(root))
    result = []
    for eid, event in sorted(events(root).items(), key=lambda item: (item[1]['observed_at'], item[0])):
        records = history(root, eid)
        latest = records[-1] if records else {}
        state = latest.get('status', 'pending')
        if state not in TERMINAL:
            result.append({'event_id': eid, 'status': state, 'affected_page_ids': event['affected_page_ids'],
                           'follow_up_owner': latest.get('follow_up_owner'), 'question': latest.get('question'),
                           'follow_up_on': latest.get('follow_up_on')})
    return result


def search(root, query):
    terms = re.findall(r'\w+', query.lower())
    if not terms:
        return []
    results = []
    for pid, (path, meta, body) in page_map(root).items():
        text = (meta['title'] + ' ' + body).lower()
        score = sum(text.count(term) for term in terms)
        if score:
            matched = next((line for line in body.splitlines() if any(term in line.lower() for term in terms)), '')
            verified = meta['last_verified']
            stale = verified is None or (meta['review_every_days'] > 0 and (date.today() - date.fromisoformat(verified)).days > meta['review_every_days'])
            results.append({'id': pid, 'path': path.relative_to(root).as_posix(), 'status': meta['status'],
                            'owner': meta['owner'], 'last_verified': verified, 'stale': stale,
                            'verified_scope': meta['verified_scope'], 'excerpt': matched[:350], 'score': score})
    return sorted(results, key=lambda row: (-row['score'], row['id']))[:8]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate').add_argument('--base', help='Git revision for immutable-history comparison')
    sub.add_parser('queue')
    sub.add_parser('search').add_argument('query')
    for name in ('submit', 'receipt'):
        sub.add_parser(name).add_argument('file', type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'validate':
            require_valid(validate(root, args.base))
            print('PASS: page metadata, local references, events and receipt histories')
        elif args.command == 'queue':
            print(json.dumps(queue(root), indent=2))
        elif args.command == 'search':
            print(json.dumps(search(root, args.query), indent=2))
        else:
            op = submit if args.command == 'submit' else append_receipt
            value = read_json(args.file)
            if value.get('schema_version') != 2:
                if args.command == 'submit':
                    exact_retry = events(root).get(value.get('event_id')) == value
                else:
                    exact_retry = value in history(root, value.get('event_id', ''))
                    if 'sequence' not in value:
                        exact_retry = any({key: item for key, item in old.items() if key != 'sequence'} == value
                                          for old in history(root, value.get('event_id', '')))
                if not exact_retry:
                    raise ValueError('new CLI records require schema_version 2; v1 is historical read/exact-retry only')
            path, status = op(root, value)
            print(f'{status}: {path.relative_to(root)} (local only)')
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
