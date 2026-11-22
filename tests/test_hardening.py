"""Real SQLite failure modes, retention, backup/recovery, and process restart."""
import io
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import app as server
import database


class HardeningTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = str(Path(folder.name) / 'test.sqlite3')
        self.app = server.create_app({'TESTING': True, 'SECRET_KEY': 'testing', 'DATABASE': self.path})
        with self.app.app_context():
            database.init_db()
        self.client = self.app.test_client()
        self.client.get('/history')
        with self.client.session_transaction() as session:
            self.owner, self.token = session['owner_id'], session['csrf_token']

    def save(self):
        return database.save_search(self.owner, {'skills': ['Python']}, {'role': 'Developer'}, [])

    def test_sqlite_lock_preserves_results_and_returns_clear_warning(self):
        blocker = sqlite3.connect(self.path)
        self.addCleanup(blocker.close)
        blocker.execute('BEGIN EXCLUSIVE')
        with self.app.app_context():
            database.get_db().execute('PRAGMA busy_timeout=1')
            with patch.object(server, 'infer_job_seniority', side_effect=lambda jobs: jobs), \
                 patch.object(server, 'parse_resume', return_value={'skills': ['Python']}), \
                 patch.object(server, 'search_jobs', return_value=[]), \
                 patch.object(server, 'rank_jobs', return_value=[]):
                response = self.client.post('/match', data={'resume': (io.BytesIO(b'demo'), 'a.pdf')})
            self.assertEqual(response.status_code, 503)
            self.assertIn(b'Results could not be saved', response.data)
            self.assertNotIn(b'database is locked', response.data)
        blocker.rollback()
        with self.app.app_context():
            self.assertEqual(database.list_searches(self.owner), [])

    def test_read_only_delete_fails_without_removing_row(self):
        with self.app.app_context():
            key = self.save()
            database.get_db().execute('PRAGMA query_only=ON')
            response = self.client.post('/history/' + key + '/delete', data={'csrf_token': self.token})
            self.assertEqual(response.status_code, 503)
            self.assertIn(b'History temporarily unavailable', response.data)
            self.assertIsNotNone(database.get_search(self.owner, key))

    def test_read_only_delete_all_and_failed_backup_preserve_data(self):
        with self.app.app_context():
            key = self.save()
            database.get_db().execute('PRAGMA query_only=ON')
            response = self.client.post('/history/delete-all', data={'csrf_token': self.token})
            self.assertEqual(response.status_code, 503)
            self.assertIsNotNone(database.get_search(self.owner, key))
            with self.assertRaises(OSError):
                database.backup_database(Path(self.path).parent / 'missing' / 'backup.sqlite3')
            self.assertIsNotNone(database.get_search(self.owner, key))

    def test_corrupt_json_and_missing_schema_are_generic(self):
        with self.app.app_context():
            key = self.save()
            with database.get_db() as db:
                db.execute('UPDATE searches SET profile_json=? WHERE id=?', ('private corrupt content', key))
        response = self.client.get('/history/' + key)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private corrupt content', response.data)
        empty = server.create_app({'TESTING': True, 'SECRET_KEY': 'test',
                                   'DATABASE': str(Path(self.path).with_name('uninitialized.sqlite3'))})
        self.assertEqual(empty.test_client().get('/history').status_code, 503)

    def test_retention_preview_apply_and_boundary(self):
        now = datetime(2026, 11, 18, tzinfo=timezone.utc)
        with self.app.app_context():
            keys = [self.save() for _ in range(3)]
            for key, age in zip(keys, [31, 30, 2]):
                with database.get_db() as db:
                    db.execute('UPDATE searches SET created_at=? WHERE id=?',
                               ((now - timedelta(days=age)).isoformat().replace('+00:00', 'Z'), key))
            self.assertEqual(database.prune_history(now=now), 1)
            self.assertEqual(len(database.list_searches(self.owner)), 3)
            self.assertEqual(database.prune_history(now=now, dry_run=False), 1)
            self.assertIsNotNone(database.get_search(self.owner, keys[1]))
            self.assertEqual(database.prune_history(now=now, dry_run=False), 0)
            self.app.config['HISTORY_RETENTION_DAYS'] = 0
            with self.assertRaises(ValueError):
                database.prune_history(now=now, dry_run=False)

    def test_retention_cli_defaults_to_preview(self):
        with self.app.app_context():
            key = self.save()
            with database.get_db() as db:
                db.execute("UPDATE searches SET created_at='2000-01-01T00:00:00Z' WHERE id=?", (key,))
        runner = self.app.test_cli_runner()
        preview = runner.invoke(args=['prune-history'])
        self.assertEqual(preview.exit_code, 0)
        self.assertIn('Would delete 1', preview.output)
        with self.app.app_context():
            self.assertIsNotNone(database.get_search(self.owner, key))
        applied = runner.invoke(args=['prune-history', '--apply'])
        self.assertEqual(applied.exit_code, 0)
        self.assertIn('Deleted 1', applied.output)

    def test_backup_restores_data_and_refuses_overwrite(self):
        output = Path(self.path).with_name('backup.sqlite3')
        with self.app.app_context():
            key = self.save()
        result = self.app.test_cli_runner().invoke(args=['backup-db', str(output)])
        self.assertEqual(result.exit_code, 0, result.output)
        with self.app.app_context():
            database.delete_owner_data(self.owner)
        restored = server.create_app({'TESTING': True, 'SECRET_KEY': 'testing', 'DATABASE': str(output)})
        with restored.app_context():
            self.assertIsNotNone(database.get_search(self.owner, key))
            self.assertEqual(database.get_db().execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertNotEqual(self.app.test_cli_runner().invoke(args=['backup-db', str(output)]).exit_code, 0)

    def test_restart_in_separate_process_preserves_cookie_and_history(self):
        first_code = '''
import json
from app import create_app
import database
app=create_app({'TESTING':True,'SECRET_KEY':'process-test'})
with app.app_context(): database.init_db()
c=app.test_client()
c.get('/history')
with c.session_transaction() as s: owner=s['owner_id']
with app.app_context(): key=database.save_search(owner, {'skills':['Python']}, {'role':'Restart test'}, [])
print(json.dumps({'id':key,'cookie':c.get_cookie('session').value}))
'''
        env = dict(os.environ, DATABASE_PATH=self.path)
        first = subprocess.run([sys.executable, '-c', first_code], env=env, capture_output=True, text=True, check=True)
        second_code = '''
import json,sys
from app import create_app
r=json.loads(sys.stdin.read())
app=create_app({'TESTING':True,'SECRET_KEY':'process-test'})
c=app.test_client()
c.set_cookie('session',r['cookie'])
response=c.get('/history/'+r['id'])
assert response.status_code==200 and b'Restart test' in response.data
print('reopened')
'''
        second = subprocess.run([sys.executable, '-c', second_code], input=first.stdout, env=env,
                                capture_output=True, text=True, check=True)
        self.assertEqual(second.stdout.strip(), 'reopened')

    def test_form_validation_handles_unicode_and_huge_page(self):
        self.assertEqual(self.client.post('/history/delete-all', data={'csrf_token': '日本語'}).status_code, 400)
        self.assertEqual(self.client.get('/history?page=' + '9' * 100).status_code, 400)

    def test_provider_exception_details_are_not_disclosed(self):
        with patch.object(server, 'parse_resume', side_effect=RuntimeError('private-provider-text')):
            with self.assertLogs(self.app.logger, level='ERROR') as logs:
                response = self.client.post('/match', data={'resume': (io.BytesIO(b'demo'), 'a.pdf')})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private-provider-text', response.data)
        self.assertNotIn('private-provider-text', ''.join(logs.output))


if __name__ == '__main__':
    unittest.main()
