# ADR-001: SQLite as Entity Store

- Date: 2026-03-15
- Status: Accepted
- Decision: Store all entities (preindividuals, tasks, artifacts) in a single SQLite database (`.t9.db`) with FTS5 virtual tables for full-text search.
- Rationale:
  - Needed local-first storage to escape Notion API dependency (source of infinite debugging loops).
  - All agents (cc/cx/gm) access SQLite natively via Python stdlib `sqlite3`.
  - WAL mode supports concurrent reads across multiple sessions.
  - FTS5 provides grep-level search at the DB level, preventing a custom index Build.
  - Single-file DB simplifies Syncthing synchronization.
- Alternatives rejected:
  - **Notion DB**: API instability, encoding issues, 2000-char limit, external dependency.
  - **JSON files**: Write conflicts, poor search performance.
  - **PostgreSQL/MySQL**: Server management overhead, overkill for solo operation.
  - **Filesystem + grep**: No metadata management, no state transition tracking.
- Outcome:
  - `t9_seed.py` serves as the single entry point for all DB access.
  - Core schema: `entities` table (id, filepath, filename, phase, metadata JSON, body_preview, file_hash).
  - `transitions` table tracks full state transition history.
  - `relates` table records transductive relationships between entities.
  - `_migrate_db()` handles schema migrations safely (ALTER TABLE only, never DROP TABLE).

## Simondon Mapping
Associated milieu — SQLite serves as the shared environment (milieu) mediating individuation across all entities.
