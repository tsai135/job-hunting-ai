"""Explicit opt-in live validation, using a synthetic resume and disposable data.

RUN_LIVE_WORKFLOW=1 python -m unittest discover -s tests -p test_live_workflow.py -v

This calls OpenAI and Adzuna, starts the real matching microservice, and may
fetch Chroma's default embedding model. It can incur normal provider charges.
No production history or existing Chroma database is used.
"""
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import app as server
import database
from services import resume_parser, job_data, matching, seniority
from workflow_fixture import synthetic_resume_pdf


@unittest.skipUnless(os.getenv('RUN_LIVE_WORKFLOW') == '1',
                     'Live workflow is opt-in; API credentials and model/network access required.')
class LiveWorkflowTests(unittest.TestCase):
    def test_live_outputs_persist_reopen_and_delete(self):
        missing = [name for name in ('OPENAI_API_KEY', 'ADZUNA_APP_ID', 'ADZUNA_APP_KEY') if not os.getenv(name)]
        if missing:
            self.skipTest('Missing configuration: ' + ', '.join(missing))
        from werkzeug.serving import make_server
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'JOB_SEARCH_DEMO': '0'}):
                spec = importlib.util.spec_from_file_location('live_matching_service', Path('job-match-service/app.py'))
                micro = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(micro)
                http_server = make_server('127.0.0.1', 0, micro.app)
                thread = threading.Thread(target=http_server.serve_forever, daemon=True)
                thread.start()
                try:
                    app = server.create_app({'TESTING': True, 'SECRET_KEY': 'live-disposable-test',
                                             'DATABASE': str(Path(folder) / 'searches.sqlite3')})
                    with app.app_context():
                        database.init_db()
                    actual = {}

                    def parse(data):
                        actual['profile'] = resume_parser.parse_resume(data)
                        return actual['profile']

                    def retrieve(profile, preferences):
                        actual['jobs'] = job_data.search_jobs(profile, preferences)
                        return actual['jobs']

                    def rank(profile, jobs):
                        actual['matches'] = matching.rank_jobs(profile, jobs)
                        return actual['matches']

                    def adjust(profile, matches):
                        actual['adjusted'] = seniority.adjust_seniority(profile, matches)[:10]
                        return actual['adjusted']

                    client = app.test_client()
                    with patch.object(matching, 'MATCH_SERVICE_URL', f'http://127.0.0.1:{http_server.server_port}'), \
                         patch.object(server, 'parse_resume', side_effect=parse), \
                         patch.object(server, 'search_jobs', side_effect=retrieve), \
                         patch.object(server, 'rank_jobs', side_effect=rank), \
                         patch.object(server, 'adjust_seniority', side_effect=adjust):
                        response = client.post('/match', data={'resume': (io.BytesIO(synthetic_resume_pdf()), 'synthetic.pdf'),
                                                              'role': 'Python Developer', 'location': 'New York'})
                    self.assertEqual(response.status_code, 200, 'Live pipeline failed; inspect provider configuration without disclosing credentials.')
                    self.assertTrue(actual['jobs'], 'Adzuna returned no jobs; cannot validate nonempty matching output.')
                    self.assertTrue(actual['matches'], 'Matching returned no jobs.')
                    with client.session_transaction() as session:
                        owner, token = session['owner_id'], session['csrf_token']
                    with app.app_context():
                        key = database.list_searches(owner)[0]['id']
                        saved = database.get_search(owner, key)
                        self.assertEqual(saved['profile'], actual['profile'])
                        self.assertEqual(saved['matches'], actual['adjusted'])
                    self.assertEqual(client.get('/history/' + key).status_code, 200)
                    restarted = server.create_app({'TESTING': True, 'SECRET_KEY': 'live-disposable-test', 'DATABASE': app.config['DATABASE']})
                    after_restart = restarted.test_client()
                    after_restart.set_cookie('session', client.get_cookie('session').value)
                    self.assertEqual(after_restart.get('/history/' + key).status_code, 200)
                    self.assertEqual(after_restart.post('/history/' + key + '/delete', data={'csrf_token': token}).status_code, 303)
                    self.assertEqual(after_restart.get('/history/' + key).status_code, 404)
                finally:
                    http_server.shutdown()
                    thread.join(timeout=5)
                    http_server.server_close()
