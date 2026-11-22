"""Offline persistence tests; external search/embedding services are test doubles."""
import importlib
import io
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import database

# Import the real Flask app without loading Chroma models or calling job APIs.
stubs = {}
for module, function in [('services.resume_parser', 'parse_resume'),
                         ('services.job_data', 'search_jobs'),
                         ('services.matching', 'rank_jobs')]:
    stub = types.ModuleType(module)
    setattr(stub, function, lambda *args: None)
    stubs[module] = stub

stubs['services.resume_parser'].UnreadablePDFError = type(
    'UnreadablePDFError', (Exception,), {}
)

with patch.dict(sys.modules, stubs):
    server = importlib.import_module('app')


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = str(Path(folder.name) / 'db.sqlite3')
        self.app = server.create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret', 'DATABASE': self.path})
        with self.app.app_context():
            database.init_db()
        self.a, self.b = self.app.test_client(), self.app.test_client()

    def complete(self, client):
        with patch.object(server, 'parse_resume', return_value={'skills': ['Python']}), \
             patch.object(server, 'search_jobs', return_value=[]), \
             patch.object(server, 'rank_jobs', return_value=[{'job': {'id': 'one', 'title': 'Developer', 'description': 'Python'}, 'score': 90}]):
            return client.post('/match', data={'resume': (io.BytesIO(b'demo'), 'a.pdf'), 'role': 'Developer'})

    def identity(self, client):
        with client.session_transaction() as session:
            return session['owner_id'], session['csrf_token']

    def test_complete_save_reopen_and_retrieve(self):
        self.assertEqual(self.complete(self.a).status_code, 200)
        owner, _ = self.identity(self.a)
        with self.app.app_context():
            database.init_db()
            summary = database.list_searches(owner)[0]
            row = database.get_search(owner, summary['id'])
            self.assertEqual(row['profile']['skills'], ['Python'])
            self.assertEqual(row['matches'][0]['score'], 90)
        self.assertIn(b'Developer', self.a.get('/history').data)
        self.assertIn(b'Developer', self.a.get('/history/' + summary['id']).data)

    def test_cross_session_access_and_csrf(self):
        self.complete(self.a)
        owner, token = self.identity(self.a)
        self.b.get('/history')
        _, other_token = self.identity(self.b)
        with self.app.app_context():
            key = database.list_searches(owner)[0]['id']
        self.assertEqual(self.b.get('/history/' + key).status_code, 404)
        self.assertNotIn(b'Developer', self.b.get('/history').data)
        self.assertEqual(self.b.post('/history/' + key + '/delete', data={'csrf_token': other_token}).status_code, 404)
        self.assertEqual(self.a.post('/history/' + key + '/delete').status_code, 400)
        self.assertEqual(self.a.get('/history/' + key + '/delete').status_code, 405)
        self.assertEqual(self.a.post('/history/' + key + '/delete', data={'csrf_token': token}).status_code, 303)
        self.assertEqual(self.a.get('/history/' + key).status_code, 404)

    def test_delete_all_preserves_other_owner(self):
        self.complete(self.a)
        self.complete(self.b)
        _, token = self.identity(self.a)
        self.assertEqual(self.a.post('/history/delete-all', data={'csrf_token': token}).status_code, 303)
        self.assertNotIn(b'Developer', self.a.get('/history').data)
        self.assertIn(b'Developer', self.b.get('/history').data)

    def test_validation_and_json_failure_leave_no_row(self):
        with self.app.app_context():
            for args in [('', {}, {}, []), ('a', [], {}, []), ('a', {}, {}, [float('nan')])]:
                with self.assertRaises((TypeError, ValueError)):
                    database.save_search(*args)
            self.assertEqual(database.list_searches('a'), [])
            with self.assertRaises(ValueError):
                database.list_searches('a', limit=101)
            self.assertIsNone(database.get_search('a', 'missing'))
        self.assertEqual(self.a.get('/history?page=bad').status_code, 400)

    def test_storage_failures_are_generic(self):
        with patch.object(database, 'save_search', side_effect=sqlite3.OperationalError('sensitive detail')):
            response = self.complete(self.a)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b'sensitive detail', response.data)
        with patch.object(database, 'list_searches', side_effect=sqlite3.OperationalError('sensitive detail')):
            self.assertEqual(self.a.get('/history').status_code, 503)

    def test_failed_service_does_not_save(self):
        with patch.object(
            server, 'parse_resume', side_effect=RuntimeError('failure')
        ), patch.object(database, 'save_search') as save:

            response = self.a.post(
                '/match',
                data={'resume': (io.BytesIO(b'demo'), 'a.pdf')}
            )

            self.assertEqual(response.status_code, 503)
            save.assert_not_called()

    def test_transaction_rolls_back(self):
        with self.app.app_context():
            db = database.get_db()
            with self.assertRaises(sqlite3.IntegrityError):
                with db:
                    db.execute("INSERT INTO searches VALUES ('x','a','now','{}','{}','[]')")
                    db.execute("INSERT INTO searches VALUES ('x','a','now','{}','{}','[]')")
            self.assertEqual(database.list_searches('a'), [])

    def test_cli_and_session_survive_app_restart(self):
        result = self.app.test_cli_runner().invoke(args=['init-db'])
        self.assertEqual(result.exit_code, 0)
        self.complete(self.a)
        cookie = self.a.get_cookie('session')
        restarted = server.create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret', 'DATABASE': self.path})
        client = restarted.test_client()
        client.set_cookie('session', cookie.value)
        self.assertIn(b'Developer', client.get('/history').data)


if __name__ == '__main__':
    unittest.main()
