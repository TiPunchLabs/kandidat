# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- APIFlask integration replacing Flask — auto-generated OpenAPI spec and Swagger UI documentation at `/docs`
- Help page (`/help`) with keyboard shortcuts and feature reference
- About page (`/about`) with version display and project info
- Configurable server port via `PORT` environment variable (default: 8000)

### Changed

- Replaced "Vibrant" theme (indigo, light) with "Dim" theme (GitHub Dark Dimmed inspired, slate blue accent `#539BF5`)
- Themes are now: Precision (light) | Dim (mid-dark) | Dark (full dark) | Pastel (warm light)

### Fixed

- Dark mode: text invisible in table cells (Bootstrap `--bs-emphasis-color` override not applied)
- Dark mode: Bootstrap `.text-muted` class using hardcoded gray color invisible on dark backgrounds
- Dark mode: CV preview modal and content using hardcoded `white` background
- Dark mode: Bootstrap CSS variables (`--bs-body-color`, `--bs-emphasis-color`, `--bs-secondary-color`, `--bs-heading-color`, `--bs-border-color`) now overridden for both Dark and Dim themes

### Previous

- Dashboard with sortable/filterable table of candidatures
- Detail page with metadata, markdown content, file management
- Status workflow with enforced transitions (brouillon -> envoyee -> ... -> archivee)
- Status history timeline on detail page with chronological tracking
- Creation form with cible selection and file upload
- Statistics page (by status, type, priority, category, timeline)
- Obsidian dashboard regeneration (00-Dashboard.md)
- Target companies management (cibles) with drag-and-drop ordering
- Full-text search across candidatures and files
- REST API for all resources (candidatures, cibles, fichiers, stats, search)
- SQLite migration from legacy markdown/frontmatter data
- Custom CSS design system ("Precision Instrument")
- Pydantic validation for all inputs
- pytest test suite (154 tests)
- LinkedIn field on target companies (cible detail, forms, API)
- AI-powered company enrichment via Tavily web search + LLM structured extraction
- Tavily API key configuration in Settings page with connectivity test
- Enrichment preview page with checkboxes for company info and contacts before applying
- `complete()` method on LLM Protocol for generic prompt completion (used by enrichment)
- Docker port changed to 8000
