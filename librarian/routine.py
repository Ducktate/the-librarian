"""One bounded local librarian run; the user's scheduler invokes this wrapper."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
import subprocess

from . import knowledge


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def overdue(root):
    result = []
    for pid, (_, meta, _) in knowledge.page_map(root).items():
        verified = meta['last_verified']
        if verified is None or (meta['review_every_days'] > 0 and
                (date.today() - date.fromisoformat(verified)).days > meta['review_every_days']):
            result.append(pid)
    return result


@contextmanager
def routine_lock(root):
    runtime = root / '.runtime'
    runtime.mkdir(exist_ok=True)
    path = runtime / 'routine.lock'
    try:
        stream = path.open('x', encoding='utf-8')
    except FileExistsError:
        raise ValueError('Librarian run already locked. Verify the process before removing a stale .runtime/routine.lock.') from None
    try:
        with stream:
            json.dump({'pid': os.getpid(), 'started_at': now()}, stream)
        yield runtime
    finally:
        path.unlink(missing_ok=True)


def make_prompt(root, queue, stale):
    instructions = (root / 'prompts/LIBRARIAN-RUN.md').read_text(encoding='utf-8')
    context = {'private_brain_path': str(root),
               'pending_events': [{'event_id': row['event_id'], 'status': row['status']} for row in queue],
               'overdue_page_ids': stale}
    return instructions + '\n\n## Current run context\n\n' + json.dumps(context, indent=2) + '\n'


def run_routine(root, dry_run=False, force=False):
    knowledge.require_valid(knowledge.validate(root))
    cfg = knowledge.read_json(root / 'librarian.json')
    queue = knowledge.queue(root)
    stale = overdue(root)
    prompt = make_prompt(root, queue, stale)
    if dry_run:
        print(prompt)
        print('DRY RUN: no runner invoked; no schedule installed or verified.')
        return 0
    if cfg.get('mode') != 'company' or cfg.get('owner') == 'unassigned':
        raise ValueError('Configure your private company copy before running a librarian.')
    if not queue and not stale and not force:
        print('No pending events or overdue pages; no agent invocation.')
        return 0
    runner = cfg.get('runner', {})
    command = runner.get('command')
    timeout = runner.get('timeout_seconds', 1800)
    if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise ValueError('Configure runner.command as a nonempty argument array; see docs/SCHEDULING.md.')
    if not any('{prompt_file}' in arg for arg in command):
        raise ValueError('Runner command must consume {prompt_file}.')
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 7200:
        raise ValueError('runner.timeout_seconds must be 1..7200.')
    with routine_lock(root) as runtime:
        prompt_file = runtime / 'run-prompt.md'
        prompt_file.write_text(prompt, encoding='utf-8')
        args = [arg.replace('{prompt_file}', str(prompt_file)).replace('{root}', str(root)) for arg in command]
        report = {'started_at': now(), 'state': 'running', 'pending_events': len(queue), 'overdue_pages': len(stale)}
        report_path = runtime / 'last-run.json'
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        try:
            with (runtime / 'runner-output.log').open('w', encoding='utf-8') as output:
                result = subprocess.run(args, cwd=root, stdin=subprocess.DEVNULL, stdout=output,
                                        stderr=subprocess.STDOUT, text=True, timeout=timeout, shell=False)
            report.update(state='runner-exited' if result.returncode == 0 else 'failed', exit_code=result.returncode)
            code = 0 if result.returncode == 0 else 1
        except (OSError, subprocess.SubprocessError) as exc:
            report.update(state='failed', error=str(exc))
            code = 1
        report['finished_at'] = now()
        report['scope'] = 'Wrapper execution only; verify actual agent changes, authority, publication and scheduled execution separately.'
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(f'Librarian wrapper: {report["state"]}; inspect {report_path}')
        return code
