"""Public CLI regressions: fictional evidence in disposable template copies only."""
from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from librarian import cli, knowledge as k
from librarian.__main__ import main


ROOT = Path(__file__).resolve().parent.parent


class CliAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'fictional brain'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            '.git', '.runtime', '__pycache__', '.venv'))

    def invoke(self, *args, status=0):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([*map(str, args), '--root', str(self.root)])
        value = json.loads(output.getvalue())
        self.assertEqual(result, status, value)
        self.assertEqual(value['ok'], status == 0, value)
        self.assertEqual(set(value), {'ok', 'command', 'data', 'errors', 'scope'})
        self.assertTrue(value['scope'])
        self.assertEqual(bool(value['errors']), status != 0)
        return value

    def write(self, value, name='input.json'):
        path = Path(self.temp.name) / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def event(self, observed_at=None):
        event = k.read_json(self.root / 'examples/contribution.json')
        if observed_at:
            event.update(event_id=str(uuid.uuid4()), observed_at=observed_at)
        return event

    def receipt(self, event=None, recorded_at=None, sequence=1):
        receipt = k.read_json(self.root / 'examples/needs-context.json')
        receipt['sequence'] = sequence
        if event:
            receipt['event_id'] = event['event_id']
        if recorded_at:
            receipt['recorded_at'] = recorded_at
        return receipt

    def assert_rejected_event(self, event):
        self.invoke('update', 'lint', self.write(event), status=2)
        self.invoke('update', 'submit', self.write(event), status=2)
        self.assertEqual(k.event_paths(self.root), [])

    def test_public_template_is_valid_empty_and_not_schedule_verified(self):
        self.assertEqual(k.event_paths(ROOT), [], 'public upstream must contain no live intake')
        audit = self.invoke('audit')['data']
        self.assertTrue(audit['valid'])
        self.assertFalse(audit['immutable_history_checked'])
        self.assertTrue(any('Without --base' in note for note in audit['limitations']))
        health = self.invoke('health')['data']
        self.assertEqual(health['mode'], 'template')
        self.assertTrue(health['read_ready'])
        self.assertFalse(health['contribute_ready'])
        self.assertFalse(health['schedule_verified'])

    def test_query_pagination_is_bounded_and_stable(self):
        first = self.invoke('query', 'company', '--limit', 1)['data']
        self.assertGreater(first['total'], 1)
        self.assertEqual(len(first['results']), 1)
        self.assertEqual(first['next_offset'], 1)
        second = self.invoke('query', 'company', '--offset', 1, '--limit', 1)['data']
        self.assertEqual(second['total'], first['total'])
        self.assertNotEqual(first['results'][0]['id'], second['results'][0]['id'])
        self.assertEqual(first['results'], self.invoke('query', 'company', '--limit', 1)['data']['results'])
        last = self.invoke('query', 'company', '--offset', first['total'], '--limit', 1)['data']
        self.assertEqual(last['results'], [])
        self.assertIsNone(last['next_offset'])
        for bounds in (('--offset', -1), ('--limit', 0), ('--limit', 1001)):
            with self.subTest(bounds=bounds):
                self.invoke('query', 'company', *bounds, status=2)

    def test_read_uses_exact_ids_and_pages_body_without_losing_file_hash(self):
        page = self.root / 'wiki/company/overview.md'
        _, body = k.parse_page(page)
        lines = body.splitlines()
        chunks = []
        for offset in range(0, len(lines), 2):
            data = self.invoke('read', 'company-overview', '--offset', offset, '--limit', 2)['data']
            chunks.extend(data['body'].splitlines())
            self.assertEqual(data['content_sha256'], hashlib.sha256(page.read_bytes()).hexdigest())
            self.assertEqual(data['total_lines'], len(lines))
        self.assertEqual(chunks, lines)
        self.invoke('read', 'company', status=2)
        self.invoke('read', 'wiki/company/overview.md', status=2)

    def test_draft_is_explicitly_incomplete_and_cannot_overwrite_pages(self):
        output = Path(self.temp.name) / 'draft.json'
        draft = self.invoke('update', 'draft', '--agent', 'fictional-agent',
                            '--session', 'fictional-session', '--machine', 'fictional-host',
                            '--output', output)['data']
        self.assertTrue(draft['draft'])
        self.assertIsNone(draft['observed_at'])
        self.invoke('update', 'lint', output, status=2)
        self.invoke('update', 'submit', output, status=2)
        self.assertEqual(k.event_paths(self.root), [])
        page = self.root / 'wiki/company/overview.md'
        before = page.read_bytes()
        self.invoke('update', 'draft', '--output', page, status=2)
        self.assertEqual(page.read_bytes(), before)
        self.invoke('update', 'draft', '--output', output, status=3)
        self.assertEqual(k.read_json(output), draft)

    def test_submit_retry_conflict_and_audit_pending_flag(self):
        event = self.event()
        path = self.write(event)
        self.invoke('update', 'lint', path)
        stored = self.invoke('update', 'submit', path)['data']
        destination = self.root / stored['path']
        before = destination.read_bytes()
        self.assertTrue(stored['local_only'])
        self.assertEqual(self.invoke('update', 'submit', path)['data']['status'], 'unchanged')
        event['summary']['impact'] = 'FICTIONAL: changed assertion'
        self.invoke('update', 'submit', self.write(event), status=2)
        self.assertEqual(destination.read_bytes(), before)
        self.assertEqual(self.invoke('audit')['data']['flags'][0]['flag'], 'pending')

    def test_malformed_records_and_unknown_schema_return_json_errors(self):
        malformed = Path(self.temp.name) / 'malformed.json'
        malformed.write_text('{not JSON', encoding='utf-8')
        self.invoke('update', 'lint', malformed, status=2)
        for value in ([], {'schema_version': 99}, {'schema_version': 2}):
            with self.subTest(value=value):
                self.assert_rejected_event(value)

    def test_v2_requires_real_identity_distinct_revisions_and_exact_paths(self):
        for field in ('agent', 'session', 'machine'):
            for identity in ('REPLACE-WITH-ID', 'unknown', 'unassigned', ''):
                with self.subTest(field=field, identity=identity):
                    event = self.event()
                    event['author'][field] = identity
                    self.assert_rejected_event(event)
        event = self.event()
        event['context']['change_revision'] = event['context']['base_revision']
        self.assert_rejected_event(event)
        for path in ('../export.py', '/src/export.py', 'src\\export.py', './src/export.py', 'src//export.py', 'src/*.py'):
            with self.subTest(path=path):
                event = self.event()
                event['changes'][0]['paths'][0]['path'] = path
                self.assert_rejected_event(event)

    def test_v2_evidence_guards_do_not_allow_unsupported_assertions(self):
        for label in ('verification', 'delivery', 'decision'):
            with self.subTest(label=label):
                event = self.event()
                event[label]['evidence'] = (['examples/not-cited.md'] if label == 'verification'
                    else [{'type': 'source_code' if label == 'delivery' else 'owner_approval',
                           'source': 'examples/not-cited.md', 'detail': 'FICTIONAL: uncited evidence'}])
                self.assert_rejected_event(event)
        event = self.event()
        event['delivery']['evidence'] = []
        self.assert_rejected_event(event)
        event = self.event()
        event['verification'] = {'result': 'passed', 'evidence': []}
        self.assert_rejected_event(event)
        event = self.event()
        event['changes'][0]['paths'][0]['before'] = event['changes'][0]['paths'][0]['after']
        self.assert_rejected_event(event)
        event = self.event()
        event['kind'] = 'decision'
        event['decision']['state'] = 'accepted'
        self.assert_rejected_event(event)
        for state in ('tested', 'merged', 'deployed', 'client_qualified'):
            with self.subTest(delivery_state=state):
                event = self.event()
                event['delivery']['state'] = state
                event['claims'][0]['delivery_state'] = state
                self.assert_rejected_event(event)

    def test_v2_context_repository_must_trace_to_a_changed_repository(self):
        event = self.event()
        self.assertEqual(event['context']['repository'], 'fictional-repo')
        self.invoke('update', 'lint', self.write(event))
        for repository in (None, 'fictional-other-repo'):
            with self.subTest(repository=repository):
                event = self.event()
                event['context']['repository'] = repository
                self.assert_rejected_event(event)

    def test_receipt_identity_run_id_and_sequence_are_enforced(self):
        event = self.event()
        k.submit(self.root, event)
        for change in ({'run_id': 'not-a-uuid'}, {'sequence': 2}, {'draft': True},
                       {'actor': 'different-agent'}, {'recorded_at': '2026-01-01T11:59:00Z'}):
            with self.subTest(change=change):
                receipt = self.receipt(event)
                receipt.update(change)
                self.invoke('receipt', 'record', self.write(receipt), status=2)
        receipt = self.receipt(event)
        receipt['operator']['session'] = 'unknown'
        self.invoke('receipt', 'record', self.write(receipt), status=2)
        self.assertEqual(k.history(self.root, event['event_id']), [])
        receipt = self.receipt(event)
        path = self.write(receipt)
        stored = self.invoke('receipt', 'record', path)['data']
        before = (self.root / stored['path']).read_bytes()
        self.assertEqual(self.invoke('receipt', 'record', path)['data']['status'], 'unchanged')
        receipt['reason'] = 'FICTIONAL: conflicting rewrite'
        self.invoke('receipt', 'record', self.write(receipt), status=2)
        self.assertEqual((self.root / stored['path']).read_bytes(), before)
        flag = self.invoke('audit')['data']['flags'][0]
        self.assertEqual(flag['flag'], 'needs_context')
        self.assertTrue(flag['owner'])
        self.assertTrue(flag['required_evidence'])

    def test_daily_utc_bounds_exclude_future_events_and_later_receipts(self):
        old = self.event('2026-01-01T12:00:00Z')
        before = self.event('2026-01-01T23:59:59Z')
        start = self.event('2026-01-02T00:00:00Z')
        cutoff = self.event('2026-01-02T12:00:00Z')
        future = self.event('2026-01-02T12:00:01Z')
        end = self.event('2026-01-03T00:00:00Z')
        for event in (old, before, start, cutoff, future, end):
            k.submit(self.root, event)
        k.append_receipt(self.root, self.receipt(old, '2026-01-02T00:00:00Z'))
        filed = self.receipt(old, '2026-01-02T12:00:01Z', sequence=2)
        filed.update(status='filed', affected_paths=['wiki/company/overview.md'])
        k.append_receipt(self.root, filed)
        report = self.invoke('report', 'daily', '--date', '2026-01-02', '--timezone', 'UTC',
                             '--as-of', '2026-01-02T12:00:00Z')['data']
        rows = {row['event_id']: row for row in report['executive_changes']}
        self.assertEqual(set(rows), {start['event_id'], cutoff['event_id']})
        self.assertEqual(len(report['audit']), 1)
        self.assertEqual(report['audit'][0]['event_id'], old['event_id'])
        self.assertEqual(report['audit'][0]['status'], 'needs_context')
        operator = next(row for row in report['sessions'] if row['role'] == 'librarian_operator')
        self.assertEqual(operator['session'], 'fictional-review-session')
        self.assertEqual(operator['run_id'], self.receipt()['run_id'])
        self.assertEqual(len(report['flags']), 1)
        self.assertEqual(report['flags'][0]['event_id'], old['event_id'])
        final = self.invoke('report', 'daily', '--date', '2026-01-02', '--timezone', 'UTC',
                            '--as-of', '2026-01-04T00:00:00Z')['data']
        rows = {row['event_id']: row for row in final['executive_changes']}
        self.assertEqual(set(rows), {old['event_id'], start['event_id'], cutoff['event_id'], future['event_id']})
        self.assertFalse(rows[old['event_id']]['observed_today'])
        self.assertTrue(rows[old['event_id']]['filed_today'])
        self.assertEqual(rows[old['event_id']]['status_as_of'], 'filed')

    def test_daily_dst_windows_are_calendar_days_not_fixed_24_hours(self):
        try:
            ZoneInfo('America/New_York')
        except ZoneInfoNotFoundError:
            self.skipTest('America/New_York timezone data unavailable')
        for day, start, end, hours in (
            ('2026-03-08', '2026-03-08T05:00:00+00:00', '2026-03-09T04:00:00+00:00', 23),
            ('2026-11-01', '2026-11-01T04:00:00+00:00', '2026-11-02T05:00:00+00:00', 25),
        ):
            with self.subTest(day=day):
                report = cli.daily(self.root, day, 'America/New_York', '2026-12-01T00:00:00Z')
                window = report['window']
                self.assertEqual(window, {'start_utc': start, 'end_utc_exclusive': end})
                self.assertEqual((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds(), hours * 3600)

    def test_accepted_decision_report_preserves_evidence_and_authority_limitations(self):
        event = self.event()
        event.update(kind='decision', decision_authority='FICTIONAL: designated owner acceptance')
        event['decision'] = {'state': 'accepted', 'authority': 'fictional-owner',
                             'evidence': [{'type': 'owner_approval', 'source': 'examples/evidence.md',
                                           'detail': 'FICTIONAL: owner approved this scoped decision'}]}
        k.submit(self.root, event)
        report = self.invoke('report', 'daily', '--date', '2026-01-01', '--timezone', 'UTC',
                             '--as-of', '2026-01-02T00:00:00Z')['data']
        row = report['executive_changes'][0]
        self.assertEqual(row['decision'], event['decision'])
        self.assertEqual(row['sources'], event['sources'])
        self.assertEqual(row['author']['session'], event['author']['session'])
        self.assertTrue(any('not independently verified authority' in note for note in report['limitations']))
        self.assertTrue(any('not a historical reconstruction' in note for note in report['limitations']))

    def test_report_rejects_ambiguous_scope_and_cannot_overwrite_intake(self):
        for args in (('--date', 'not-a-date', '--timezone', 'UTC'),
                     ('--date', '2026-01-01', '--timezone', 'Not/AZone'),
                     ('--date', '2026-01-01', '--timezone', 'UTC', '--as-of', '2026-01-01T12:00:00')):
            with self.subTest(args=args):
                self.invoke('report', 'daily', *args, status=2)
        event = self.event()
        k.submit(self.root, event)
        path = k.event_destination(self.root, event)
        before = path.read_bytes()
        self.invoke('report', 'daily', '--date', '2026-01-01', '--timezone', 'UTC',
                    '--output', path, status=2)
        self.assertEqual(path.read_bytes(), before)

    def test_public_upstream_remote_blocks_intake_in_disposable_copy(self):
        for args in (('init',), ('remote', 'add', 'upstream', 'git@github.com:Ducktate/the-librarian.git')):
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True, text=True)
        event = self.event()
        result = self.invoke('update', 'submit', self.write(event), status=2)
        self.assertIn('Public upstream', ' '.join(result['errors']))
        self.assertEqual(k.event_paths(self.root), [])

    def test_legacy_history_is_reported_without_upgrade_and_new_v1_is_rejected(self):
        event = k.read_json(self.root / 'examples/contribution-v1.json')
        self.invoke('update', 'submit', self.write(event), status=2)
        path, _ = k.submit(self.root, event)  # Existing low-level v1 compatibility.
        before = path.read_bytes()
        self.assertEqual(self.invoke('update', 'submit', self.write(event))['data']['status'], 'unchanged')
        report = self.invoke('report', 'daily', '--date', '2026-01-01', '--timezone', 'UTC',
                             '--as-of', '2026-01-02T00:00:00Z')['data']
        self.assertTrue(report['executive_changes'][0]['legacy_contract'])
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(any(row['flag'] == 'legacy_contract' for row in self.invoke('audit')['data']['flags']))

    def test_audit_base_detects_edits_to_committed_intake(self):
        path, _ = k.submit(self.root, self.event())
        for args in (('init',), ('add', '.'), ('-c', 'user.name=Fictional',
                     '-c', 'user.email=fictional@example.invalid', 'commit', '-m', 'Fictional fixture')):
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True, text=True)
        self.assertTrue(self.invoke('audit', '--base', 'HEAD')['data']['immutable_history_checked'])
        event = k.read_json(path)
        event['summary']['impact'] = 'FICTIONAL: rewritten history'
        path.write_text(json.dumps(event), encoding='utf-8')
        result = self.invoke('audit', '--base', 'HEAD', status=2)
        self.assertTrue(any('immutable history changed' in error for error in result['errors']))

    def test_source_checkout_checks_exact_revisions_and_changed_filenames(self):
        source = Path(self.temp.name) / 'fictional source'
        source.mkdir()

        def git(*args):
            return subprocess.run(['git', *args], cwd=source, check=True,
                                  capture_output=True, text=True).stdout.strip()

        git('init')
        (source / 'changed.bin').write_bytes(b'\xfffictional-before')
        (source / 'unchanged.py').write_text('# Fictional unchanged module\n', encoding='utf-8')
        git('add', '.')
        git('-c', 'user.name=Fictional', '-c', 'user.email=fictional@example.invalid',
            'commit', '-m', 'Fictional base')
        base = git('rev-parse', 'HEAD')
        (source / 'changed.bin').write_bytes(b'\xfffictional-after')
        git('add', 'changed.bin')
        git('-c', 'user.name=Fictional', '-c', 'user.email=fictional@example.invalid',
            'commit', '-m', 'Fictional change')
        change = git('rev-parse', 'HEAD')
        event = self.event()
        event['context'].update(repository='fictional-repo', base_revision=base, change_revision=change)
        event['changes'][0]['commits'] = [change]
        event['changes'][0]['paths'][0]['path'] = 'changed.bin'
        self.invoke('update', 'lint', self.write(event), '--source-checkout', source)
        event['changes'][0]['paths'][0]['path'] = 'unchanged.py'
        failure = self.invoke('update', 'lint', self.write(event), '--source-checkout', source, status=2)
        self.assertTrue(any('not changed between exact source revisions' in error for error in failure['errors']))
        event['context']['change_revision'] = 'c' * 40
        failure = self.invoke('update', 'lint', self.write(event), '--source-checkout', source, status=2)
        self.assertTrue(any('exact source Git commit unavailable' in error for error in failure['errors']))
        self.assertEqual(k.event_paths(self.root), [])


if __name__ == '__main__':
    unittest.main()
