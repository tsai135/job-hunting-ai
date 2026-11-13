"""SQLite persistence for completed matching searches.

Uses SQLite and Flask. Importing this module does not create a database.
Register init_app(app), then explicitly run the init-db Flask command.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import click
from flask import current_app, g

# ---------------------------------------------------------------------------
# 1. PROPOSED SCHEMA
# ---------------------------------------------------------------------------
# One row is a completed search. JSON retains the existing service dictionaries.
# These snapshots are not the job pipeline's searchable catalog.
# Raw resume uploads, passwords, and embeddings are not stored here.
SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    preferences_json TEXT NOT NULL,
    matches_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS searches_owner_created
    ON searches(owner_id, created_at DESC, id DESC);
"""

# ---------------------------------------------------------------------------
# 2. CONNECTION AND INITIALIZATION
# ---------------------------------------------------------------------------
def get_db():
    """Reuse one connection within the current Flask application context."""
    if 'job_search_db' not in g:
        connection = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        connection.row_factory = sqlite3.Row
        g.job_search_db = connection
    return g.job_search_db


def close_db(_error=None):
    """Release the context's connection, including when a request fails."""
    connection = g.pop('job_search_db', None)
    if connection is not None:
        connection.close()


def init_db():
    """Create missing tables/indexes without resetting existing data.

    This initializes the draft schema; it does not migrate changed schemas.
    """
    database_path = current_app.config['DATABASE']
    # sqlite's in-memory database needs no directory (and lasts one connection).
    if str(database_path) != ':memory:':
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    with db:
        db.executescript(SCHEMA)


def init_app(app):
    """Register configuration, cleanup, and an explicit initialization command."""
    app.config.setdefault('DATABASE', str(Path(app.instance_path) / 'job_search.sqlite3'))
    app.teardown_appcontext(close_db)

    @app.cli.command('init-db')
    def init_db_command():
        """Create missing search-history tables."""
        init_db()
        click.echo('Database initialized.')

# ---------------------------------------------------------------------------
# 3. SAVE ONE COMPLETED SEARCH
# ---------------------------------------------------------------------------
def save_search(owner_id, profile, preferences, matches):
    """Save a completed search atomically and return its unique identifier.

    Caller must supply a trusted server-issued owner ID. This function does
    not authenticate users; never treat a form-supplied ID as proof of identity.
    Call within a Flask application/request context after database setup.
    """
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise ValueError('owner_id must be a nonempty server-issued identifier.')
    if not isinstance(profile, dict) or not isinstance(preferences, dict):
        raise TypeError('profile and preferences must be dictionaries.')
    if not isinstance(matches, list):
        raise TypeError('matches must be a list.')

    # Serialize first: invalid JSON data fails before any row is inserted.
    # Disallow NaN/infinity so stored snapshots contain valid JSON numbers.
    payload = [json.dumps(value, allow_nan=False)
               for value in (profile, preferences, matches)]
    search_id = uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    db = get_db()
    # The context manager commits on success and rolls back on failure.
    # Bound parameters keep submitted text separate from SQL instructions.
    with db:
        db.execute(
            'INSERT INTO searches '
            '(id, owner_id, created_at, profile_json, preferences_json, matches_json) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (search_id, owner_id, created_at, *payload),
        )
    return search_id


def _owner(owner_id):
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise ValueError('A nonempty owner ID is required.')


def get_search(owner_id, search_id):
    _owner(owner_id)
    row = get_db().execute('SELECT * FROM searches WHERE owner_id=? AND id=?',
                           (owner_id, search_id)).fetchone()
    if row is None:
        return None
    return {'id': row['id'], 'created_at': row['created_at'],
            'profile': json.loads(row['profile_json']),
            'preferences': json.loads(row['preferences_json']),
            'matches': json.loads(row['matches_json'])}


def list_searches(owner_id, limit=20, offset=0):
    _owner(owner_id)
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError('Invalid history pagination.')
    rows = get_db().execute(
        'SELECT id, created_at, preferences_json FROM searches WHERE owner_id=? '
        'ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?',
        (owner_id, limit, offset)).fetchall()
    return [{'id': row['id'], 'created_at': row['created_at'],
             'preferences': json.loads(row['preferences_json'])} for row in rows]


def delete_search(owner_id, search_id):
    _owner(owner_id)
    db = get_db()
    with db:
        result = db.execute('DELETE FROM searches WHERE owner_id=? AND id=?', (owner_id, search_id))
    return result.rowcount == 1


def delete_owner_data(owner_id):
    _owner(owner_id)
    db = get_db()
    with db:
        result = db.execute('DELETE FROM searches WHERE owner_id=?', (owner_id,))
    return result.rowcount
