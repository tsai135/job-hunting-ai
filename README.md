
# Job Hunting AI — CS 467 Capstone

A Flask web app that accepts a resume and job preferences, searches for jobs, ranks matches, and displays recommendations.

## Current Status

End-to-end local prototype integrating:

- Resume parsing using OpenAI
- Job retrieval using the Adzuna API
- Job matching and ranking
- Session-based career preferences
- SQLite search-history persistence

## Run Locally

Requires Python 3.10+.

### macOS / Linux

From the repository folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Environment Configuration

For live integrations, copy `.env.example` to `.env` and configure:

- `OPENAI_API_KEY` — OpenAI resume parsing
- `ADZUNA_APP_ID` — Adzuna application ID
- `ADZUNA_APP_KEY` — Adzuna application key

Set `JOB_SEARCH_DEMO=0` to disable fallback demo job postings when Adzuna credentials are unavailable.

For deployed environments, configure a stable `FLASK_SECRET_KEY` (or `SECRET_KEY`) to protect Flask sessions.

### Initialize the Database

Before starting the application for the first time, run:

```sh
python -m flask --app app init-db
```

This creates the SQLite database and required tables without deleting existing searches.

### Start the Application

```sh
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Upload a readable PDF resume and enter your preferred role and location to generate job recommendations.

The `/test-results` route is available for testing the frontend using sample jobs without uploading a resume.

## Search-History Persistence

Completed matching requests save the parsed profile, career preferences, and ranked job results in SQLite.

Open `/history` (or click **HISTORY** in the navigation) to:

- View previous searches
- Reopen saved job recommendations
- Delete individual searches
- Delete all saved searches

Search history belongs to the current browser session. User accounts and authentication are not implemented.

Keep your browser cookies to retain access to your saved history.

SQLite data and the locally generated session-signing key are stored in the ignored `instance/` directory.

See [Database Design and Team Review Decisions](docs/database-design.md) for additional implementation details.

## Testing

Run the offline persistence test suite:

```sh
python -m unittest discover -s tests -v
```

These tests use mocked services and do not require live OpenAI or Adzuna API calls.


## Persistence validation and deployment preparation

See [database operations](docs/database-operations.md) for setup, retention,
consistent backups, recovery, and deployment limits.
```sh
# Preview rows older than HISTORY_RETENTION_DAYS (default 30).
python -m flask --app app prune-history
# Apply only after reviewing the policy and preview.
python -m flask --app app prune-history --apply
# Snapshot to an existing private directory; refuses to overwrite a file.
python -m flask --app app backup-db /absolute/private/backup/searches-2026-11-22.sqlite3
```

Cleanup is a creation-age limit, including abandoned sessions, rather than
last-activity tracking. The deployment operator must schedule daily cleanup and
backup rotation; neither is scheduled automatically here. For HTTPS, configure
`SESSION_COOKIE_SECURE=1` and a stable private `FLASK_SECRET_KEY`.

The default tests run without provider API calls or embedding-model downloads:

```sh
python -m unittest discover -s tests -v
```

They include actual PDF extraction, service response normalization, seniority
reranking, the matching microservice, Chroma, Flask, and SQLite. API responses
and embeddings are fixtures; this does **not** prove live integration.

An optional live test sends a synthetic resume to actual providers and runs the
current matching microservice using disposable data. Normal API charges and
model downloads may apply:

```sh
RUN_LIVE_WORKFLOW=1 python -m unittest discover -s tests -p test_live_workflow.py -v
```

This requires `OPENAI_API_KEY`, `ADZUNA_APP_ID`, and `ADZUNA_APP_KEY` in local `.env`.
Missing configuration causes a skip, not a live-test pass. The live test is not
run as part of the offline suite.
