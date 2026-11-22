# Database operations and deployment — Clifton Brown

## Setup

Run commands from the project root in an activated Python 3.10+ environment:

```sh
python -m pip install -r requirements.txt
python -m flask --app app init-db
```

`init-db` creates missing tables/indexes and preserves existing searches. It is
not a migration tool. If a schema changes later, use reviewed migrations.

SQLite defaults to `instance/job_search.sqlite3`. Set an absolute `DATABASE_PATH`
for deployment, on a persistent volume writable by the app user. Do not use an
ephemeral container filesystem. Keep database files, session keys, and backups out
of Git and restrict filesystem access to the service operator.

For actual searches, configure `.env` locally with `OPENAI_API_KEY`,
`ADZUNA_APP_ID`, and `ADZUNA_APP_KEY`. Set `JOB_SEARCH_DEMO=0` when validating live
Adzuna results. Start the separate matching service in a second terminal:

```sh
cd job-match-service
python app.py
```

Then start the main app from the project root with `python app.py`. The matching
service defaults to port 3117; set `MATCH_SERVICE_URL` if it is hosted elsewhere.
The current service uses in-memory, per-request Chroma collections that are removed after matching. Its embedding model may need an initial download. Do not expose that service
publicly; it has no authentication. Its development entry point enables debug;
use a production WSGI server and disable debug for deployment.

## Sessions and deployment configuration

Set a stable private `FLASK_SECRET_KEY` (or `SECRET_KEY`) for all main-app workers.
For local use only, the app generates an ignored `instance/session.key`. Keep the
same signing key across restarts and restore operations so retained browser
cookies can still identify their history. Cookie contents are signed, not
secret; owner IDs are random, but the cookie is still an access credential.
Set `SESSION_COOKIE_SECURE=1` behind HTTPS. Local HTTP development needs it off.
Never use Flask's development server or debug mode for a public deployment.

History is scoped to anonymous browser sessions, not authenticated accounts.
Clearing cookies loses access; the server cannot identify the person afterward.
Every read/delete requires the signed owner ID. Deletion uses POST and a
session-bound CSRF token. There is no account-based recovery or cross-device
history. Requesting or submitting an arbitrary owner ID does not grant access.

## Retention policy proposal

Default: completed searches become eligible for deletion 30 days after creation,
including searches abandoned when a browser loses its cookie. Set a positive
integer `HISTORY_RETENTION_DAYS` to change this. This is a maximum-age policy,
not inactivity tracking: active users' old searches are eligible too.

Preview first:

```sh
python -m flask --app app prune-history
```

Apply only after reviewing the policy and preview:

```sh
python -m flask --app app prune-history --apply
```

Operators should schedule the apply command daily using the deployment's job
scheduler and monitor its exit code. No scheduler has been installed here, and
cleanup does not run on web requests. With daily cleanup, rows can remain up to
roughly 31 days. Users can delete sooner through history. The UI discloses the
configured age. Retention configuration and production schedule need team approval.

This only purges main-app SQLite search rows. It does not purge the separate
matching service (which currently removes its per-request Chroma collections). Raw PDFs are not stored by the persistence layer. Deletion
is logical; SQLite free pages and older backups can retain copies.

## Consistent backup

Use SQLite's backup API rather than copying an active database file:

```sh
python -m flask --app app backup-db /absolute/private/backup/searches-2026-11-22.sqlite3
```

The destination's parent must exist. The command creates a consistent snapshot,
checks integrity, uses restrictive initial file permissions, and refuses to
overwrite an existing path. It does not print user data. Keep backups encrypted
using your deployment's storage controls and limit access. Preserve the signing
key separately through a secret manager; do not commit it or bundle it with a
public backup. Backups contain personal profile data.

Proposed operator policy: daily encrypted backups with seven-day expiry, adjusted
to team requirements. Rotation is not automatic in this code. Honor deletion
requests when expiring backups and in any restoration process. A restored older
snapshot can reintroduce deleted rows; before reopening service, reapply any
recorded deletion requests and run retention cleanup. This prototype has no
persistent deletion ledger, so it cannot automatically honor deletions across
old backup restores. Document and review that limitation before production.

## Recovery drill

1. Stop **all** main-app workers and scheduled cleanup jobs. Keep the matching
   service distinct from this recovery; its current per-request collections are ephemeral.
2. Preserve the current database for diagnosis in restricted storage. Do not
   copy an active SQLite file or reuse stale `-wal`/`-shm` sidecars from another
   database. Have the operator perform replacement only after all connections
   are closed.
3. Check the candidate snapshot before use:

   ```sh
   python -c "import sqlite3; c=sqlite3.connect('file:/absolute/private/backup/searches-2026-11-22.sqlite3?mode=ro', uri=True); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
   ```

   Require `ok`. Confirm it is the intended backup and deployment schema.
4. Restore the verified snapshot to the configured `DATABASE_PATH` with correct
   ownership/permissions, keeping the same configured signing key. A safe drill
   can point `DATABASE_PATH` to a **copy** of the snapshot rather than replacing
   the live database.
5. Reapply deletions and preview/apply retention before resuming traffic. Do not
   run `init-db` as a substitute for restoring data; it only creates tables.
6. Restart the main app. In the same retained browser session, open `/history`,
   reopen a known search, and verify another session cannot access it. Check
   logs for generic failure events without dumping resume contents.

Automated tests verify recovery against a separate snapshot and integrity check;
no real user database was restored or purged during this work.

## Failure behavior and remaining limitations

- Failed saves show completed results with a visible **not saved** warning and
  HTTP 503. History operations show a generic retry page. No provider details or
  database tracebacks are included in these responses or main-app persistence log events. The separate seniority module still prints its own inference failures; the team should sanitize those logs before deployment.
- Corrupt JSON, missing schema, locks, and read-only failures are covered by tests.
- SQLite has limited write concurrency and local-disk assumptions. PostgreSQL,
  migrations, shared storage architecture, and load tests remain future work.
- No encryption at rest, account authentication, deletion ledger, automated backup
  rotation, or scheduler is implemented here.
- The parser's `experience_years` currently counts experience entries rather
  than elapsed years. Persistence preserves that value; the parser owner should
  resolve its semantics. No parsing or scoring logic was changed in this task.
- API versions/models, live credentials, network access, and the matching service
  determine full-pipeline availability. Offline tests do not prove live service
  availability or ranking quality.
