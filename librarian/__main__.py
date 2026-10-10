"""CLI entrypoint for The Librarian."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys

from . import knowledge
from .routine import run_routine


def configure(root, company, owner):
    config_path = root / 'librarian.json'
    cfg = knowledge.read_json(config_path)
    if cfg.get('mode') != 'template':
        raise ValueError('Company already configured; review explicit edits instead of resetting it.')
    if not company.strip() or len(company) > 120 or any(ord(c) < 32 for c in company):
        raise ValueError('Company must be a nonempty single line, at most 120 characters.')
    if owner == 'unassigned' or not re.fullmatch(r'[a-z][a-z0-9-]+', owner):
        raise ValueError('Owner must be an accountable lowercase identity, such as company-owner.')
    remotes = subprocess.run(['git', 'remote', '-v'], cwd=root, capture_output=True, text=True, timeout=10)
    # Refuse any upstream push remote, even if it was named something other than origin.
    for line in remotes.stdout.lower().splitlines():
        if '(push)' in line and re.search(r'github\.com[:/]ducktate/the-librarian(?:\.git)?(?:\s|$)', line):
            raise ValueError('Public upstream is still a push remote. Create your private copy and replace/remove that remote first.')
    knowledge.require_valid(knowledge.validate(root))
    changes = []
    for _, (path, meta, body) in knowledge.page_map(root).items():
        meta['title'] = meta['title'].replace('Your Company', company.strip())
        if meta['owner'] == 'unassigned':
            meta['owner'] = owner
        text = '---\n' + '\n'.join(k + ': ' + json.dumps(v) for k, v in meta.items())
        text += '\n---\n' + body.replace('Your Company', company.strip()).replace(
            'Accountable company owner: unassigned until configure/setup.',
            f'Accountable company owner: {owner}.') + '\n'
        changes.append((path, text))
    cfg.update(mode='company', company=company.strip(), owner=owner)
    with knowledge.write_lock(root):
        for path, text in changes:
            path.write_text(text, encoding='utf-8', newline='\n')
        config_path.write_text(json.dumps(cfg, indent=2) + '\n', encoding='utf-8')
    return cfg


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in {'configure', 'routine'}:
        return knowledge.main(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['configure', 'routine'])
    parser.add_argument('--root', type=Path, default=knowledge.ROOT)
    if argv[0] == 'configure':
        parser.add_argument('--company', required=True)
        parser.add_argument('--owner', required=True)
    else:
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'configure':
            cfg = configure(args.root.resolve(), args.company, args.owner)
            print(f'Configured {cfg["company"]}; pages remain draft/unverified. Complete START-HERE.md.')
            return 0
        return run_routine(args.root.resolve(), args.dry_run, args.force)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
