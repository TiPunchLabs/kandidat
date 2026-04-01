# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-04-01

### Added

- AI-powered match scoring — evaluate CV vs job offer fit via LLM, returns score (0-100) with structured justification (strengths, weaknesses, missing skills)
- `POST /api/candidatures/{slug}/match` endpoint for match evaluation
- Match score badge (colored: red <40, orange 40-69, green 70+) on detail page and dashboard table
- Collapsible match details panel on detail page (strengths, weaknesses, missing skills)
- Configurable match prompts in Settings page (system prompt, user prompt) with collapsible sections
- MCP `evaluate_match` tool (23 tools total)
- Architecture Decision Records (`docs/adr/`) — 8 ADRs documenting key architectural choices
- Makefile with MCP server targets (`make mcp-dev`, `make mcp-prod`)

### Changed

- Renamed `doc/` directory to `docs/` for consistency
- Updated all documentation references to use `docs/` path
- Fixed Settings keys documentation to match actual provider-specific keys (`llm_ollama_url`, `llm_claude_api_key`, etc.)
- GitLab → GitHub mirror restricted to protected branches only (main)
- Bumped version to 0.2.0

## [0.1.0] - 2026-03-15

### Added

- APIFlask integration replacing Flask — auto-generated OpenAPI spec and Swagger UI documentation at `/docs`
- Help page (`/help`) with keyboard shortcuts and feature reference
- About page (`/about`) with version display and project info
- Configurable server port via `PORT` environment variable (default: 8000)
- AI-powered company enrichment via Tavily web search + LLM structured extraction
- Tavily API key configuration in Settings page with connectivity test
- Enrichment preview page with checkboxes for company info and contacts before applying
- `complete()` method on LLM Protocol for generic prompt completion (used by enrichment)
- AI-powered CV adaptation via LLM with PDF/DOCX export (WeasyPrint + python-docx)
- Settings page for CV reference upload, LLM provider configuration, and prompt customization
- MCP Server (TypeScript, streamable HTTP) — 22 tools exposing REST API for LLM agents
- Status history timeline with comments on detail page
- Target companies management (cibles) with contacts and drag-and-drop ordering
- Dashboard with sortable/filterable table of candidatures
- Detail page with metadata, markdown content, file management
- Status workflow with enforced transitions (brouillon → envoyee → ... → archivee)
- Creation form with cible selection and file upload
- Statistics page (by status, type, priority, category, timeline)
- Full-text search across candidatures and files
- REST API for all resources (candidatures, cibles, fichiers, stats, search)
- Custom CSS design system with 4 themes (Precision, Dim, Dark, Pastel)
- Pydantic validation for all inputs
- pytest test suite (318 tests)
- GitLab CI pipeline (lint, test, security, build, release, deploy via bastion)
- PostgreSQL 17 support with SQLite fallback for local dev
- Dockhost deployment via Ansible + GitLab Container Registry

### Changed

- Replaced "Vibrant" theme with "Dim" theme (GitHub Dark Dimmed inspired)

### Fixed

- Dark mode: text invisible in table cells, `.text-muted` color, CV preview modal background
- Dark mode: Bootstrap CSS variables properly overridden for Dark and Dim themes

[Unreleased]: https://gitlab.com/tipunchlabs/kandidat/-/compare/v0.2.0...HEAD
[0.2.0]: https://gitlab.com/tipunchlabs/kandidat/-/compare/v0.1.0...v0.2.0
[0.1.0]: https://gitlab.com/tipunchlabs/kandidat/-/tags/v0.1.0
