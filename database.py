"""SQLite persistence for completed searches."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def init_db(path: str | Path) -> None:
    database = sqlite3.connect(path)
    try:
        database.executescript(SCHEMA)
        database.commit()
    finally:
        database.close()


def save_search(
    path: str | Path,
    owner_id: str,
    profile: dict[str, Any],
    preferences: dict[str, Any],
    matches: list[dict[str, Any]],
) -> str:
    if not owner_id:
        raise ValueError("owner_id is required.")
    search_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    database = sqlite3.connect(path)
    try:
        database.execute(
            """INSERT INTO searches
            (id, owner_id, created_at, profile_json, preferences_json, matches_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                search_id,
                owner_id,
                created_at,
                json.dumps(profile),
                json.dumps(preferences),
                json.dumps(matches),
            ),
        )
        database.commit()
    finally:
        database.close()
    return search_id
