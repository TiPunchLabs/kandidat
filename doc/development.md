# Development guide

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [direnv](https://direnv.net/) (optional, auto-activates the venv)
- [pass](https://www.passwordstore.org/) (optional, secret management)
- WeasyPrint system dependencies for PDF export ([installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html))

## Installation

```bash
# Clone and enter the project
cd kandidat

# Activate direnv (creates the venv + installs deps)
direnv allow

# Or manually
uv sync
```

## Commands

| Action | Command |
| --- | --- |
| Start the server | `uv run python main.py` |
| Run tests | `uv run pytest` |
| Verbose tests | `uv run pytest -v` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Security scan | `uv run bandit -c pyproject.toml -r services/ api/ routes.py app.py` |


## Code structure

```text
app.py              Flask application factory
main.py             Entry point (python main.py)
config.py           Configuration (FT_DATA_DIR)
routes.py           Web routes (Blueprint "main")
api/                REST API (Blueprint "api", prefix /api)
  candidatures.py   Application endpoints + CV adapt/convert/save
  other_routes.py   Company, search, stats, dashboard, enrichment endpoints
  settings.py       Settings API (LLM config, CV reference, prompts, Tavily)
services/           Business logic (no direct Flask imports except current_app)
  candidature.py    Application CRUD + status transitions
  cibles.py         Target companies + contacts management
  fichiers.py       File upload/delete
  dashboard.py      Obsidian markdown regeneration
  database.py       SQLAlchemy models + migrations
  schemas.py        Pydantic validation schemas
  search.py         Full-text search
  settings.py       Settings CRUD (CV reference, LLM config, prompts, Tavily)
  cv_adapter.py     CV adaptation orchestrator (LLM context + prompts)
  cv_converter.py   HTML→PDF (WeasyPrint) + HTML→DOCX (BeautifulSoup)
  cible_enricher.py Company enrichment (Tavily + LLM extraction)
  llm/              LLM provider package
    __init__.py     Provider Protocol + factory
    ollama.py       Ollama provider (local, httpx)
    claude.py       Claude provider (distant, anthropic SDK)
templates/          Jinja2 templates
static/             Custom CSS
tests/              pytest tests
doc/                Technical documentation
```

## Conventions

### Code

- **Style**: ruff (line-length=120, target py312, rules E/F/I/W)
- **Validation**: Pydantic schemas for all inputs
- **ORM**: Flask-SQLAlchemy, no raw SQL except in migrations
- **Lazy imports**: Optional heavy dependencies (httpx, anthropic, weasyprint, python-docx, beautifulsoup4, lxml, tavily) are imported inside functions to avoid startup failures when not installed

### Commits

Conventional Commits format (commitizen configured):

```text
feat: add status history timeline
fix: prevent duplicate cible creation
refactor: extract file upload logic to service
docs: add architecture documentation
```

### Branches

```text
{type}/{kebab-description}
feat/status-history
fix/cible-cascade-delete
```

### Tests

- One file per layer: `test_candidature.py` (service), `test_routes.py` (web), `test_api.py` (API)
- Feature-specific tests: `test_cv_adapt.py`, `test_cible_enricher.py`
- Fixtures in `conftest.py`: in-memory database, seed data, files on disk via `tmp_path`
- Convention: one class per feature, descriptive `test_*` methods

### Pre-commit hooks

Install hooks:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

Active hooks: ruff, bandit, gitleaks, commitizen, yamllint, markdownlint, codespell.

## Adding an API endpoint

1. Add the Pydantic schema in `services/schemas.py`
2. Add the business logic in `services/`
3. Add the endpoint in `api/candidatures.py`, `api/settings.py`, or `api/other_routes.py`
4. Add the web route in `routes.py` if needed
5. Add tests in the appropriate `tests/test_*.py` file

## Adding a migration

Migrations are managed in `services/database.py` via `_migrate_*()` functions called in `init_app()`. Pattern:

```python
def _migrate_new_feature():
    """Description of the migration."""
    with db.engine.connect() as conn:
        # Check if already applied
        # Apply changes
        conn.commit()
```

## Adding a new LLM provider

1. Create `services/llm/new_provider.py` implementing the `LLMProvider` Protocol
2. Register the provider in `get_provider()` factory in `services/llm/__init__.py`
3. Add configuration fields in the settings page (`templates/settings.html`)
4. Add tests in `tests/test_llm.py`
