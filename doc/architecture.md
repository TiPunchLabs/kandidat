# Architecture

## Overview

```text
  Claude Desktop /           MCP Protocol               ┌──────────────────┐
  Claude Code         ◄── streamable HTTP ──►           │  MCP Server (TS) │
  (LLM agent)              port 3001                    │  mcp/src/        │
                                                        │  22 tools        │
                                                        │  1 resource      │
                                                        └────────┬─────────┘
                                                                 │ HTTP/JSON
                                                                 ▼
  Browser ──────────────────────────────────────────────────────────────────
                    │                                            │
                    ▼                                            ▼
                    ┌─────────────────────────────────────────────┐
                    │              Flask Application               │
                    │                 (app.py)                     │
                    ├──────────────────┬──────────────────────────┤
                    │                  │                          │
               routes.py          api/                    templates/
           (Blueprint "main")  (Blueprint "api")         (Jinja2)
            HTML pages         JSON endpoints
                    │                  │
                    └────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │    services/     │
                    │  Business logic  │
                    ├─────────────────┤
                    │ candidature.py  │  CRUD + status transitions
                    │ cibles.py      │  Target companies + contacts
                    │ search.py      │  Hybrid search (DB + files)
                    │ dashboard.py   │  Obsidian markdown gen
                    │ fichiers.py    │  File upload/delete
                    │ schemas.py     │  Pydantic validation
                    │ settings.py    │  Settings CRUD (CV ref, LLM, Tavily)
                    │ cv_adapter.py  │  CV adaptation orchestrator (LLM)
                    │ cv_converter.py│  HTML→PDF + HTML→DOCX conversion
                    │ cible_enricher │  Enrichment (Tavily + LLM)
                    │ llm/           │  LLM provider package
                    │   __init__.py  │    Protocol + factory
                    │   ollama.py    │    Ollama provider (local)
                    │   claude.py    │    Claude provider (distant)
                    ├─────────────────┤
                    │  database.py    │  SQLAlchemy models + migrations
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  kandidat.db    │
                    │    (SQLite)     │
                    └─────────────────┘
```

## Principles

- **SQLite as source of truth**: all data lives in the database, no markdown parsing at runtime
- **Pydantic validation**: all API/form inputs go through schemas
- **Status transitions**: strict state machine (draft -> sent -> ... -> archived)
- **Atomic file writes**: dashboard written via `tempfile` + `os.replace`
- **Cascade delete**: deleting an application removes DB files + disk directory
- **Provider Protocol**: LLM providers follow a `typing.Protocol` for extensibility

## Data model

```text
cibles (1) ──────< candidatures (1) ──────< fichiers
   │                      │
   └──< contacts          └──────< historique_statuts

settings (key/value pairs for global configuration)
```

| Table | Primary key | Relationships |
| --- | --- | --- |
| `cibles` | `id` (auto) | 1:N to candidatures, 1:N to contacts |
| `contacts` | `id` (auto) | FK `cible_id`, cascade delete |
| `candidatures` | `slug` (kebab-case) | FK `cible_id`, 1:N to fichiers, 1:N to historique |
| `fichiers` | `id` (auto) | FK `slug`, unique (slug, nom) |
| `historique_statuts` | `id` (auto) | FK `slug`, cascade delete |
| `settings` | `key` (text) | Standalone key/value store (CV ref, LLM config, prompts) |

## Status state machine

```text
brouillon ──► envoyee ──► relancee ──► entretien ──► acceptee ──► archivee
    │             │            │            │             │
    └─► archivee  └─► sans-reponse ◄───────┘   refusee ──► archivee
                  └─► archivee                    │
                                                  └─► archivee
```

## Web layer: two blueprints

| Blueprint | Prefix | Role |
| --- | --- | --- |
| `main` | `/` | HTML pages (dashboard, detail, create, stats, cibles, company detail, search, settings, CV preview/loading, enrichment loading/preview) |
| `api` | `/api` | JSON endpoints (CRUD applications, companies, contacts, files, stats, search, settings, CV adapt/convert/save, enrichment) |

## CV adaptation flow

```text
detail.html                cv_loading.html           cv_preview.html
"Adapter mon CV"  ──►  Loading spinner  ──►  iframe preview (sandbox)
                        fetch /api/.../               │
                        cv/adapt                      ├─► Confirmer → POST /api/.../cv/save → PDF+DOCX
                                                      ├─► Relancer → retour loading
                                                      └─► Annuler  → retour detail
```

## Cible enrichment flow

```text
cible_detail.html          cible_enrich_loading.html    cible_enrich_preview.html
"Enrichir via IA"  ──►  Loading spinner  ──►  Checkboxes (current vs. suggested)
                        fetch POST /api/                │
                        cibles/{id}/enrich              ├─► Appliquer → POST /api/.../enrich/apply
                        (Tavily search                  │     → update cible + create contacts
                         + LLM extraction)              ├─► Relancer → retour loading
                                                        └─► Annuler  → retour cible detail
```

### Enrichment orchestrator

```text
services/cible_enricher.py
  1. Tavily search: "{company} site officiel linkedin"     → company_results
  2. Tavily search: "{company} contacts dirigeants"        → contact_results
  3. LLM complete(): extract structured JSON               → {company, contacts}
  4. Return suggestions for user review (preview page)
  5. apply_enrichment(): save accepted fields via update_cible() + create_contact()
```

### LLM provider architecture

```text
services/llm/__init__.py
  LLMProvider (Protocol)           get_provider() factory
       │                                │
       ├── complete()                  reads settings:
       ├── adapt_cv()                   llm_provider, llm_url,
       ├── health_check()              llm_model, llm_api_key
       │
       ├── OllamaProvider
       │   (httpx → /v1/chat)
       │
       └── ClaudeProvider
           (anthropic SDK)
```

## Files on disk

```text
FT_DATA_DIR/
├── kandidat.db
├── 00-Dashboard.md          (generated by services/dashboard.py)
└── candidatures/
    ├── acme-corp/
    │   ├── offre.md
    │   ├── lm.md
    │   ├── cv_adapte_acme-corp.pdf    (generated)
    │   ├── cv_adapte_acme-corp.docx   (generated)
    │   └── coaching/
    │       └── phase1.md
    └── beta-inc/
        └── ...
```

Physical files are referenced in the `fichiers` table with a relative path.

## MCP Server layer

The MCP server (`mcp/`) is a **semantic proxy** between an LLM agent and the kandidat API.
It adds zero business logic — all validation stays in the Flask services layer.

```text
LLM Agent                          MCP Server                    kandidat API
─────────                          ──────────                    ────────────
"List my active                    list_candidatures             GET /api/candidatures
 applications"          ──►        {statut: "envoyee"}    ──►    ?statut=envoyee
                                                                      │
                        ◄──        JSON response           ◄──        │
"3 applications sent"
```

### Tool categories (22 total)

| Category | Tools | Annotations |
| --- | --- | --- |
| READ (8) | list/get candidatures, cibles, search, stats, settings, historique | `readOnlyHint: true` |
| WRITE (7) | create/update candidatures, cibles, contacts, historique comment | `idempotentHint: true` (updates) |
| DELETE (3) | delete candidature, cible, contact | `destructiveHint: true` |
| AI (4) | enrich cible, apply enrichment, adapt CV, save CV | Mixed annotations |

### Resources

The MCP server exposes a `kandidat://enums` resource loaded from `GET /api/enums`,
providing all valid enum values and status transitions to the LLM context.

### Configuration

The MCP server always runs **locally** (on the developer's machine). Only the API target
changes depending on the environment:

| Environment | `KANDIDAT_API_URL` | Use case |
| --- | --- | --- |
| Dev local | `http://localhost:8000` | kandidat running via `uv run` or docker-compose |
| Prod dockhost | `http://kandidat.local:8000` or `http://192.168.1.90:8000` | kandidat deployed on dockhost |
