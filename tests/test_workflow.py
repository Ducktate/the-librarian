import copy
from datetime import date
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from librarian import knowledge as k
from librarian.__main__ import configure
from librarian.routine import run_routine, routine_lock

ROOT = Path(__file__).resolve().parent.parent


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'company brain'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '.runtime', '__pycache__', '.venv'))

    def event(self):
        return k.read_json(self.root / 'examples/contribution.json')

    def receipt(self):
        return k.read_json(self.root / 'examples/needs-context.json')

    def config(self, **updates):
        path = self.root / 'librarian.json'
        value = k.read_json(path)
        value.update(updates)
        path.write_text(json.dumps(value), encoding='utf-8')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, capture_output=True, text=True, check=True)

    def test_template_valid_and_live_inbox_empty(self):
        self.assertEqual(k.validate(self.root), [])
        self.assertEqual(k.queue(self.root), [])

    def test_configure_preserves_unverified_facts(self):
        cfg = configure(self.root, 'Acme Studio', 'acme-owner')
        self.assertEqual(cfg['mode'], 'company')
        page = k.page_map(self.root)['company-overview'][1]
        self.assertEqual(page['owner'], 'acme-owner')
        self.assertEqual(page['status'], 'draft')
        self.assertIsNone(page['last_verified'])
        with self.assertRaises(ValueError):
            configure(self.root, 'Another', 'new-owner')
        self.assertEqual(k.validate(self.root), [])

    def test_configure_rejects_public_push_remote(self):
        self.git('init')
        self.git('remote', 'add', 'upstream', 'git@github.com:Ducktate/the-librarian.git')
        with self.assertRaisesRegex(ValueError, 'Public upstream'):
            configure(self.root, 'Acme', 'owner')

    def test_submit_retry_conflict_and_invalid_id(self):
        event = self.event()
        path, status = k.submit(self.root, event)
        self.assertEqual(status, 'stored')
        self.assertEqual(k.submit(self.root, event), (path, 'unchanged'))
        event['proposed_change'] = 'Changed content'
        with self.assertRaisesRegex(ValueError, 'different content'):
            k.submit(self.root, event)
        event['event_id'] = '../../escape'
        with self.assertRaises(ValueError):
            k.submit(self.root, event)

    def test_missing_claim_evidence_and_decision_authority(self):
        event = self.event()
        event['claims'][0]['evidence'] = ['unknown-source']
        with self.assertRaisesRegex(ValueError, 'must appear'):
            k.submit(self.root, event)
        event = self.event()
        event['kind'] = 'decision'
        with self.assertRaisesRegex(ValueError, 'authority'):
            k.submit(self.root, event)

    def test_flag_resolve_file_publish(self):
        event = self.event()
        k.submit(self.root, event)
        flag = self.receipt()
        k.append_receipt(self.root, flag)
        self.assertEqual(k.append_receipt(self.root, flag)[1], 'unchanged')
        self.assertEqual(k.queue(self.root)[0]['status'], 'needs_context')
        filed = dict(flag, status='filed', affected_paths=['wiki/company/overview.md'],
                     verification_notes='Fictional resolving evidence inspected in disposable test.')
        k.append_receipt(self.root, filed)
        published = dict(filed, status='published', published_commit='a' * 40)
        k.append_receipt(self.root, published)
        self.assertEqual(k.queue(self.root), [])
        self.assertEqual(len(k.history(self.root, event['event_id'])), 3)
        self.assertEqual(k.validate(self.root), [])
        with self.assertRaisesRegex(ValueError, 'terminal'):
            k.append_receipt(self.root, filed)

    def test_flag_requires_context_and_publication_requires_filed(self):
        k.submit(self.root, self.event())
        flag = self.receipt()
        flag['required_evidence'] = None
        with self.assertRaisesRegex(ValueError, 'required_evidence'):
            k.append_receipt(self.root, flag)
        published = dict(self.receipt(), status='published', published_commit='a' * 40,
                         affected_paths=['wiki/company/overview.md'])
        with self.assertRaisesRegex(ValueError, 'previous filed'):
            k.append_receipt(self.root, published)

    def test_local_write_lock(self):
        with k.write_lock(self.root):
            with self.assertRaisesRegex(ValueError, 'write busy'):
                k.submit(self.root, self.event())
        self.assertFalse((self.root / '.brain-write.lock').exists())

    def test_immutable_git_history(self):
        k.submit(self.root, self.event())
        self.git('init')
        self.git('add', '.')
        self.git('-c', 'user.name=Example', '-c', 'user.email=example@example.invalid', 'commit', '-m', 'test')
        path = next((self.root / 'inbox').rglob('*.json'))
        value = k.read_json(path)
        value['proposed_change'] = 'Rewrite'
        path.write_text(json.dumps(value), encoding='utf-8')
        self.assertTrue(any('immutable history' in error for error in k.validate(self.root, 'HEAD')))

    def test_routine_dry_run_is_not_a_schedule(self):
        self.assertEqual(run_routine(self.root, dry_run=True), 0)
        self.assertFalse((self.root / '.runtime').exists())
        with self.assertRaisesRegex(ValueError, 'Configure your private'):
            run_routine(self.root)

    def test_routine_real_process_adapter_and_failure(self):
        configure(self.root, 'Acme', 'acme-owner')
        adapter = self.root / 'test-adapter.py'
        adapter.write_text('import pathlib, sys\np = pathlib.Path(sys.argv[1])\nassert "Recurring librarian run" in p.read_text()\n', encoding='utf-8')
        self.config(runner={'command':[sys.executable,str(adapter),'{prompt_file}'],'timeout_seconds':10})
        self.assertEqual(run_routine(self.root), 0)
        report = k.read_json(self.root / '.runtime/last-run.json')
        self.assertEqual(report['state'], 'runner-exited')
        self.assertIn('Wrapper execution only', report['scope'])
        adapter.write_text('raise SystemExit(7)', encoding='utf-8')
        self.assertEqual(run_routine(self.root), 1)
        self.assertEqual(k.read_json(self.root / '.runtime/last-run.json')['exit_code'], 7)

    def test_routine_missing_runner_and_overlap(self):
        configure(self.root, 'Acme', 'acme-owner')
        with self.assertRaisesRegex(ValueError, 'runner.command'):
            run_routine(self.root)
        with routine_lock(self.root):
            with self.assertRaisesRegex(ValueError, 'already locked'):
                with routine_lock(self.root):
                    pass

    def test_search_and_broken_page(self):
        self.assertTrue(k.search(self.root, 'cost'))
        path = self.root / 'wiki/company/overview.md'
        path.write_text(path.read_text(encoding='utf-8')+'\n[bad](missing.md)\n', encoding='utf-8')
        self.assertTrue(any('missing reference' in error for error in k.validate(self.root)))


if __name__ == '__main__':
    unittest.main()
