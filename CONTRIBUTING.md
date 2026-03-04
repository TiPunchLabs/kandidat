# Contributing

Contributions are welcome! Here's how to get started.

## Setup

```bash
git clone <repo-url>
cd kandidat
uv sync
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

## Development workflow

1. Create a branch: `git checkout -b feat/my-feature`
2. Make your changes
3. Run checks: `uv run ruff check . && uv run pytest`
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat: add feature`
5. Open a pull request

## Branch naming

```text
feat/short-description
fix/short-description
docs/short-description
refactor/short-description
```

## Code style

- Python 3.12+, formatted with ruff (line-length=120)
- Pydantic schemas for all input validation
- Flask-SQLAlchemy ORM, no raw SQL

## Tests

- Add tests for new features in `tests/`
- All tests must pass: `uv run pytest`
- Minimum 60% coverage

## Pre-commit hooks

Hooks run automatically on commit: ruff, bandit, gitleaks, commitizen, yamllint, markdownlint, codespell.
