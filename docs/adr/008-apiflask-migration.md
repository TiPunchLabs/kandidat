# ADR-008: Migration from Flask to APIFlask for auto-generated OpenAPI

## Status

Accepted

## Context

kandidat was originally built with plain Flask. The addition of the MCP server (ADR-003) required a well-documented REST API for the semantic proxy to target. Manually maintaining OpenAPI specs alongside the code was error-prone and duplicative. The project also needed interactive API documentation for development and debugging.

## Decision

Replace `Flask` with `APIFlask` as the application framework. APIFlask is a thin wrapper around Flask that auto-generates OpenAPI 3.x specs from route decorators and provides built-in Swagger UI.

Key changes in `app.py`:
- `APIFlask(__name__, title="kandidat API", version=..., docs_path="/docs", docs_ui="swagger-ui")` replaces `Flask(__name__)`.
- OpenAPI tags are configured via `app.config["TAGS"]` to group endpoints (Candidatures, CV, Cibles, Contacts, Enrichissement, Recherche, Statistiques, Settings).
- The OpenAPI spec is served at `/openapi.json`, interactive docs at `/docs`.
- `json_errors=False` preserves Flask's default HTML error pages for web routes while the API blueprint returns JSON.

Existing Flask patterns (blueprints, Jinja2 templates, Flask-SQLAlchemy) continue to work unchanged.

## Consequences

- Interactive Swagger UI at `/docs` accelerates API development and debugging.
- The MCP server developers can reference the live OpenAPI spec instead of reading source code.
- APIFlask is a lightweight dependency (wraps Flask, no heavy framework switch).
- Existing routes and blueprints required no changes -- APIFlask is backwards-compatible with Flask.
- OpenAPI decorators can be added incrementally to enrich the generated spec with parameter descriptions and response schemas.
