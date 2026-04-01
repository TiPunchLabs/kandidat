# Configuration

## Environment variables

| Variable | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database URI. When set, uses PostgreSQL; when absent, falls back to SQLite | _(unset = SQLite)_ |
| `KANDIDAT_ENV` | Environment selector (`dev` or `prod`). Sets data directory to `data/{env}/` | `prod` |
| `FT_DATA_DIR` | Explicit data directory override (takes priority over `KANDIDAT_ENV`) | `data/{KANDIDAT_ENV}/` |
| `SECRET_KEY` | Flask secret key for session signing | `kandidat-dev-key` |
| `PORT` | Server listen port | `8000` |
| `FLASK_DEBUG` | Enable Flask debug mode (`1` = on, `0` = off) | `1` |

## Data directory structure

Data is organized by environment under `data/`:

```text
data/
  dev/                          Development data (empty by default)
    kandidat.db                 Created on first launch
    candidatures/               Empty (tests use tmp_path)
  prod/                         Production data (real france-travail data)
    kandidat.db                 Database with imported data
    candidatures/               Real candidature folders with files
    ressources/                 Source files (cibles.md)
    00-Dashboard.md             Generated Obsidian dashboard
```

Switch environments with `KANDIDAT_ENV`:

```bash
# Production (default)
uv run python main.py

# Development
KANDIDAT_ENV=dev uv run python main.py
```

## Setting up with direnv

The project includes a `.envrc` that automates venv creation and dependency syncing:

```bash
# Auto-creates .venv, installs deps, loads secrets via pass
direnv allow
```

Secrets are loaded through [pass](https://www.passwordstore.org/):

```bash
# Store the secret key
pass insert kandidat/secret-key
```

If `pass` is not configured, the fallback dev key is used automatically.

## Flask configuration

The application uses [APIFlask](https://apiflask.com/) (a Flask extension) which auto-generates OpenAPI documentation available at `/docs` (Swagger UI) and `/openapi.json` (raw spec).

Set in `app.py` via `create_app()`:

| Config key | Value | Description |
| --- | --- | --- |
| `SQLALCHEMY_DATABASE_URI` | `DATABASE_URL` or `sqlite:///{FT_DATA_DIR}/kandidat.db` | Database URI (PG or SQLite) |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | `False` | Disable modification tracking |
| `MAX_CONTENT_LENGTH` | `10 MB` | Maximum upload file size |
| `TESTING` | `False` | Enabled in test fixtures |

## Database

The application supports two database backends:

- **PostgreSQL** (production): set `DATABASE_URL` to a SQLAlchemy-compatible URI
- **SQLite** (fallback): when `DATABASE_URL` is absent, uses `{FT_DATA_DIR}/kandidat.db`

Tables are created automatically on first run via `db.create_all()`. Migrations are applied automatically at startup (see `services/database.py`).

### PostgreSQL setup

```bash
# Example DATABASE_URL
export DATABASE_URL="postgresql+psycopg://kandidat:kandidat@localhost:5432/kandidat"

# Using docker-compose (creates the postgres service automatically)
docker compose --profile prod up -d
```

### Data migration (SQLite to PostgreSQL)

```bash
DATABASE_URL=postgresql+psycopg://kandidat:kandidat@localhost:5432/kandidat \
    uv run python scripts/migrate_sqlite_to_pg.py --source data/prod/kandidat.db
```

The migration script reads all records from SQLite and writes them to PostgreSQL via the ORM. It uses `merge()` for idempotency and resets PostgreSQL sequences after import.

### SQLite (zero-config)

No external database server is needed. The file `kandidat.db` is created automatically when `DATABASE_URL` is not set.

## LLM configuration

LLM provider settings are stored in the `settings` table (SQLite) and configured via the Settings page in the web interface (`/settings`).

### Settings stored in database

| Key | Description | Example |
| --- | --- | --- |
| `llm_provider` | Active LLM provider | `ollama` or `claude` |
| `llm_url` | Provider server URL | `http://localhost:11434` |
| `llm_model` | Model name | `llama3.2`, `claude-sonnet-4-20250514` |
| `llm_api_key` | API key (distant providers only) | `sk-ant-...` |
| `cv_reference_html` | Global reference CV (HTML content) | `<html>...</html>` |
| `cv_adapt_system_prompt` | Custom system prompt for CV adaptation | (optional, default built-in) |
| `cv_adapt_user_prompt` | Custom user prompt template for CV adaptation | (optional, default built-in) |
| `match_system_prompt` | Custom system prompt for match evaluation | (optional, default built-in) |
| `match_user_prompt` | Custom user prompt template for match evaluation | (optional, default built-in) |
| `tavily_api_key` | Tavily API key for web search (cible enrichment) | `tvly-...` |

### Ollama (local)

Requires a running [Ollama](https://ollama.com/) server. Available models are listed dynamically from the server API.

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.2
```

### Claude (distant)

Requires a valid [Anthropic API key](https://console.anthropic.com/).

A privacy warning is displayed when first using a distant provider, informing that the CV (containing personal data) will be transmitted to an external service.

## Tavily configuration (company enrichment)

The Tavily API key is configured via the Settings page in the web interface. This enables AI-powered company enrichment: web search for company information (website, LinkedIn, description) and contacts (name, role, email, phone).

Get a key at [tavily.com](https://tavily.com). The key is stored in the `settings` table as `tavily_api_key`.

Both Tavily and a LLM provider must be configured for the "Enrichir via IA" button to appear on company detail pages.

## MCP Server configuration

The MCP server (`mcp/`) is a TypeScript process that exposes kandidat's REST API as MCP tools for LLM agents.

### Environment variables

| Variable | Description | Default |
| --- | --- | --- |
| `KANDIDAT_API_URL` | Base URL of the kandidat API to proxy | `http://localhost:8000` |
| `MCP_PORT` | Port for the MCP HTTP server | `3001` |

### Installation

```bash
cd mcp
pnpm install
pnpm build
```

### Running

```bash
# Dev (kandidat running locally)
cd mcp && KANDIDAT_API_URL=http://localhost:8000 pnpm dev

# Prod (kandidat on dockhost)
cd mcp && KANDIDAT_API_URL=http://kandidat.local:8000 pnpm dev
# or
cd mcp && KANDIDAT_API_URL=http://192.168.1.90:8000 pnpm dev
```

### Claude Desktop configuration

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kandidat": {
      "url": "http://127.0.0.1:3001/mcp"
    }
  }
}
```

### Claude Code configuration

Add to `.claude/settings.json` (project) or `~/.claude/settings.json` (global):

```json
{
  "mcpServers": {
    "kandidat": {
      "url": "http://127.0.0.1:3001/mcp"
    }
  }
}
```

### Architecture note

The MCP server always runs **on your local machine**, even when pointing at the production
kandidat instance. It is a lightweight proxy that translates MCP tool calls into HTTP requests.
It contains zero business logic — all validation is enforced by the kandidat Flask API.

```text
┌────────────────┐          ┌──────────────┐          ┌──────────────────┐
│ Claude Desktop │ ──MCP──► │ MCP Server   │ ──HTTP──►│ kandidat API     │
│ (your machine) │          │ (your machine│          │ (local or        │
│                │          │  port 3001)  │          │  dockhost:8000)  │
└────────────────┘          └──────────────┘          └──────────────────┘
```
