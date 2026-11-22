"""Real module/Chroma integration with fixture API responses and test embeddings.

This is NOT a live OpenAI/Adzuna/default-model test. Only API transports and the
embedding function are replaced; extraction, normalization, scoring, and SQLite
run as implemented in the repository.
"""
import importlib.util
import io
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch, Mock

import chromadb
import numpy as np

import app as server
import database
from services import resume_parser, job_data, matching, seniority
from workflow_fixture import synthetic_resume_pdf, STRUCTURED_PROFILE


class FixtureEmbedding:
    def is_legacy(self):
        return True

    def name(self):
        return 'fixture-embedding'

    def __call__(self, input):
        return np.asarray([[1.0, 0.2 + text.lower().count('python'), 0.5] for text in input], dtype=np.float32)

    def embed_query(self, input):
        return self(input)


class ServiceContractTests(unittest.TestCase):
    def test_pipeline_service_outputs_are_stored_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            # The current service uses disposable per-request collections.
            spec = importlib.util.spec_from_file_location('matching_test_service', Path('job-match-service/app.py'))
            micro = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(micro)
            micro.embedding_function = FixtureEmbedding()
            transport = micro.app.test_client()

            def post_to_microservice(url, json, timeout):
                self.assertTrue(url.endswith('/match'))
                response = transport.post('/match', json=json)
                if response.status_code != 200:
                    raise AssertionError(response.data)
                return SimpleNamespace(raise_for_status=lambda: None, json=response.get_json)

            sdk = Mock()
            sdk.beta.chat.completions.parse.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                refusal=None, parsed=resume_parser.ResumeProfile(**STRUCTURED_PROFILE)))])
            api_job = {'id': 'fixture-1', 'title': 'Python Developer', 'description': 'Build Flask APIs with SQL.',
                       'company': {'display_name': 'Fixture Company'}, 'location': {'display_name': 'Remote'},
                       'redirect_url': 'https://example.com/fixture'}
            adzuna = SimpleNamespace(status_code=200, json=lambda: {'results': [api_job]})
            seniority_sdk = Mock()
            seniority_sdk.beta.chat.completions.parse.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                parsed=seniority.SeniorityBatch(jobs=[seniority.JobSeniority(id='fixture-1', seniority='senior')])))] )
            actual = {}

            def parse(data):
                actual['profile'] = resume_parser.parse_resume(data)
                return actual['profile']

            def search(profile, preferences):
                actual['jobs'] = job_data.search_jobs(profile, preferences)
                return actual['jobs']

            def rank(profile, jobs):
                actual['matches'] = matching.rank_jobs(profile, jobs)
                return actual['matches']

            def adjust(profile, matches):
                actual['adjusted'] = seniority.adjust_seniority(profile, matches)[:10]
                return actual['adjusted']

            app = server.create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(Path(folder) / 'db.sqlite3')})
            with app.app_context():
                database.init_db()
            client = app.test_client()
            with patch.object(seniority, 'OpenAI', return_value=seniority_sdk), \
                 patch.object(resume_parser, 'OpenAI', return_value=sdk), \
                 patch.dict(os.environ, {'ADZUNA_APP_ID': 'fixture', 'ADZUNA_APP_KEY': 'fixture', 'JOB_SEARCH_DEMO': '0'}), \
                 patch.object(job_data.requests, 'get', return_value=adzuna), \
                 patch.object(matching.requests, 'post', side_effect=post_to_microservice), \
                 patch.object(server, 'parse_resume', side_effect=parse), \
                 patch.object(server, 'search_jobs', side_effect=search), \
                 patch.object(server, 'rank_jobs', side_effect=rank), \
                 patch.object(server, 'adjust_seniority', side_effect=adjust):
                response = client.post('/match', data={'resume': (io.BytesIO(synthetic_resume_pdf()), 'synthetic.pdf'), 'role': 'Python Developer'})
            self.assertEqual(response.status_code, 200)
            sdk.beta.chat.completions.parse.assert_called_once()
            sent_messages = sdk.beta.chat.completions.parse.call_args.kwargs['messages']
            self.assertIn('Synthetic Test Candidate', sent_messages[1]['content'])
            self.assertEqual(len(actual['matches']), 1)
            self.assertEqual(actual['matches'][0]['job']['id'], 'fixture-1')
            with client.session_transaction() as session:
                owner, token = session['owner_id'], session['csrf_token']
            with app.app_context():
                key = database.list_searches(owner)[0]['id']
                saved = database.get_search(owner, key)
                self.assertEqual(saved['profile'], actual['profile'])
                self.assertEqual(saved['matches'], actual['adjusted'])
                self.assertEqual(saved['matches'][0]['seniority_penalty'], 20)
                self.assertEqual(saved['matches'][0]['job_seniority'], 'senior')
                self.assertEqual(saved['matches'][0]['score'], round(max(0, saved['matches'][0]['original_score'] - 20), 2))
                self.assertEqual(saved['preferences']['role'], 'Python Developer')
            self.assertIn(b'Python Developer', client.get('/history/' + key).data)
            self.assertEqual(client.post('/history/' + key + '/delete', data={'csrf_token': token}).status_code, 303)
            self.assertEqual(client.get('/history/' + key).status_code, 404)

    def test_invalid_pdf_is_actionable_and_not_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            app = server.create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(Path(folder) / 'db.sqlite3')})
            with app.app_context():
                database.init_db()
            with patch.object(server, 'search_jobs') as search:
                response = app.test_client().post('/match', data={'resume': (io.BytesIO(b'not a PDF'), 'invalid.pdf')})
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'Resume could not be read', response.data)
            search.assert_not_called()
