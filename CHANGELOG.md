# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
