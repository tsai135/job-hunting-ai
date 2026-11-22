# Search-history schema and interfaces

SQLite stores one completed search per row in `searches`:

| Column | Type | Purpose |
| --- | --- | --- |
| id | TEXT PRIMARY KEY | Random unique search identifier |
| owner_id | TEXT NOT NULL | Server-issued anonymous session owner |
| created_at | TEXT NOT NULL | UTC creation time |
| profile_json | TEXT NOT NULL | Parsed profile snapshot |
| preferences_json | TEXT NOT NULL | Role/location snapshot |
| matches_json | TEXT NOT NULL | Ranked job dictionaries and score components |

Index: `(owner_id, created_at DESC, id DESC)` for owner-scoped history.

`save_search(owner_id, profile, preferences, matches)` serializes JSON before an
atomic insert. Reads and deletions bind both search ID and owner ID. History
summaries omit profile and full matches. No raw PDF, credentials, or embeddings
are stored in this table. The separate matching service uses ephemeral Chroma collections for request-local job matching.

Flask accepts PDF bytes, calls `services.resume_parser.parse_resume`,
`services.job_data.search_jobs`, and `services.matching.rank_jobs`, applies `services.seniority.adjust_seniority`, keeps the top 10, then saves the
returned dictionaries without changing their structure. Job seniority is inferred before matching, and all final seniority/score metadata is retained in the saved JSON. These contracts match
the current repository. Schema and operational policy changes require team review.

See [operations, retention, backup, and recovery](database-operations.md).
