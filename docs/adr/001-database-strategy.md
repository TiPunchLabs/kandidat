# ADR-001: PostgreSQL production / SQLite dev+test fallback

## Status

Accepted

## Context

kandidat needs a relational database to store candidatures, cibles, contacts, fichiers, historique_statuts, and settings. The project is used by a single user, deployed on a dockhost VM with PostgreSQL 17 available. During development and in tests, spinning up a PostgreSQL instance adds friction and slows feedback loops.

## Decision

Use PostgreSQL as the production database and SQLite as the zero-config fallback for local development and tests.

The strategy is driven by a single environment variable `DATABASE_URL`:
- **Set** (e.g. `postgresql+psycopg://...`): use PostgreSQL via psycopg 3.
- **Absent**: fall back to a SQLite file at `{FT_DATA_DIR}/kandidat.db`.

Flask-SQLAlchemy is used as the ORM layer, providing database-agnostic model definitions. Schema migrations are handled inline at startup via `ALTER TABLE` statements wrapped in try/except blocks, using `sqlalchemy.inspect` to check existing columns (works on both engines). Tests always run against an in-memory SQLite database (`conftest.py` fixture).

A one-shot migration script (`scripts/migrate_sqlite_to_pg.py`) handles data transfer from SQLite to PostgreSQL when moving to production.

## Consequences

- Local development requires zero database setup -- just `uv run python main.py`.
- Tests run fast with in-memory SQLite and need no external services.
- Migration logic must avoid database-specific SQL (e.g. use `REAL` not `FLOAT`, `TEXT` not `VARCHAR`).
- Features using PostgreSQL-specific capabilities (e.g. JSONB, array columns) are not available; `match_details` is stored as a JSON-encoded TEXT column instead.
- The migration script must be run once when transitioning a local SQLite dataset to production PostgreSQL.
