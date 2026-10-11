"""Versioned, local contracts. Historical v1 records are never upgraded in place."""
from datetime import datetime, timezone
from pathlib import PurePosixPath
import re
import subprocess


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
        raise ValueError('timestamp must be ISO 8601 with seconds and explicit offset')
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def canonical_path(value):
    return (isinstance(value, str) and bool(value) and '\\' not in value
            and not value.startswith('/') and ':' not in value
            and not any(char in value for char in '*?[]\x00\r\n')
            and all(part not in {'', '.', '..'} for part in value.split('/'))
            and PurePosixPath(value).as_posix() == value)


def public_remote(root):
    result = subprocess.run(['git', 'remote', '-v'], cwd=root, capture_output=True, text=True, timeout=10)
    return any(re.search(r'github\.com[:/]ducktate/the-librarian(?:\.git)?/?(?:\s|$)', line.lower())
               for line in result.stdout.splitlines())


def mutation_guard(root):
    if public_remote(root):
        raise ValueError('Public upstream is configured as a remote. Company configuration and mutations require a separate private copy with that remote removed.')


def event_errors(event):
    if event.get('schema_version') != 2:
        return []
    errors = []
    try:
        timestamp(event['observed_at'])
    except ValueError as exc:
        errors.append(str(exc))
    if event.get('draft') is not False:
        errors.append('draft must be false before submission')
    sources = set(event['sources'])
    for source in sources:
        if not source.startswith('https://') and not canonical_path(source.split('#', 1)[0]):
            errors.append(f'noncanonical local source path: {source}')
    for label in ('agent', 'session', 'machine'):
        value = event['author'][label]
        if value.upper().startswith('REPLACE') or value.lower() in {'unknown', 'unassigned'}:
            errors.append(f'author.{label}: actual contributor identity required')
    context = event['context']
    if not any(change['repository'] == context['repository'] for change in event['changes']):
        errors.append('context.repository must match a repository in changes')
    if context['base_revision'] == context['change_revision']:
        errors.append('context base_revision and change_revision must distinguish base from change')
    paths = set()
    for change in event['changes']:
        if not change['commits'] and not change['pull_requests']:
            errors.append('each repository/module change needs change commits or pull requests')
        for entry in change['paths']:
            key = (change['repository'], change['module'], entry['path'])
            if key in paths:
                errors.append('duplicate repository/module path')
            paths.add(key)
            if not canonical_path(entry['path']):
                errors.append(f'noncanonical exact change path: {entry["path"]}')
            if entry['before'] == entry['after']:
                errors.append('path before and after must describe an actual change')
            if not set(entry['evidence']).issubset(sources):
                errors.append('path evidence must appear in event sources')
    for label in ('verification', 'delivery', 'decision'):
        refs = event[label]['evidence'] if label == 'verification' else [item['source'] for item in event[label]['evidence']]
        if not set(refs).issubset(sources):
            errors.append(f'{label} evidence must appear in event sources')
    delivery = event['delivery']
    if delivery['state'] not in {'unknown', 'proposed'} and not delivery['evidence']:
        errors.append('asserted delivery requires evidence')
    required_type = {'implemented': 'source_code', 'tested': 'test', 'merged': 'merge',
                     'deployed': 'deployment', 'client_qualified': 'client_acceptance'}.get(delivery['state'])
    if required_type and not any(item['type'] == required_type for item in delivery['evidence']):
        errors.append(f'{delivery["state"]} delivery requires {required_type} evidence')
    for claim in event['claims']:
        if claim['delivery_state'] != delivery['state']:
            errors.append('claim delivery_state must match typed delivery state')
    if event['verification']['result'] in {'passed', 'failed'} and not event['verification']['evidence']:
        errors.append('verification result requires evidence')
    decision = event['decision']
    if decision['state'] == 'accepted' and (not decision['authority'] or not decision['evidence'] or not event['decision_authority']):
        errors.append('accepted decision requires authority and acceptance evidence')
    if decision['state'] == 'accepted' and not any(item['type'] in {'owner_approval', 'authority_decision'} for item in decision['evidence']):
        errors.append('accepted decision requires typed owner_approval or authority_decision evidence')
    if event['kind'] == 'decision' and decision['state'] != 'accepted':
        errors.append('decision kind requires accepted decision; otherwise submit proposal')
    return errors


def receipt_errors(receipt, previous, event):
    if receipt.get('schema_version') != 2:
        return []
    errors = []
    if receipt.get('draft') is not False:
        errors.append('receipt draft must be false before record')
    for label in ('agent', 'session', 'machine'):
        value = receipt['operator'][label]
        if value.upper().startswith('REPLACE') or value.lower() in {'unknown', 'unassigned'}:
            errors.append(f'operator.{label}: actual librarian identity required')
    if receipt['actor'] != receipt['operator']['agent']:
        errors.append('actor must match operator.agent')
    try:
        if timestamp(receipt['recorded_at']) < timestamp(event['observed_at']):
            errors.append('receipt timestamp precedes event observation')
        if previous and timestamp(receipt['recorded_at']) < timestamp(previous[-1]['recorded_at']):
            errors.append('receipt timestamp precedes previous receipt')
    except ValueError as exc:
        errors.append(str(exc))
    for path in receipt['affected_paths']:
        if not canonical_path(path):
            errors.append(f'noncanonical exact affected path: {path}')
    return errors
