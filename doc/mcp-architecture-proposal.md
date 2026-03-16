# 🔌 MCP Server for kandidat — Architecture Proposal

> **Objective**: Allow an LLM agent (Claude Code / Claude Desktop) to interact with kandidat
> through natural language, reading and filling all data displayed by the application.
>
> **Audience**: Decision-maker (you). This document explains *what*, *why*, and *what trade-offs*
> so you can validate or adjust before any code is written.
>
> **Date**: 2026-03-16
> **Status**: DRAFT — awaiting review

------

## 📖 Table of Contents

1. [Mental Model](#-1-mental-model)
2. [What is MCP and Why](#-2-what-is-mcp-and-why)
3. [Current State of kandidat](#-3-current-state-of-kandidat)
4. [Proposed Architecture](#-4-proposed-architecture)
5. [Complete Tool Catalog](#-5-complete-tool-catalog)
6. [Gaps to Fill Before Building](#-6-gaps-to-fill-before-building)
7. [What Needs Human Confirmation](#-7-what-needs-human-confirmation)
8. [Implementation Plan](#-8-implementation-plan)
9. [Open Questions for You](#-9-open-questions-for-you)
10. [Glossary](#-10-glossary)

------

## 🧠 1. Mental Model

### Where MCP sits

```text
 You (natural language)
  │
  ▼
┌──────────────────────┐
│  Claude Desktop /    │   "Cree une candidature chez Datadog
│  Claude Code         │    pour un poste de SRE, priorite haute"
└──────────┬───────────┘
           │ MCP Protocol (streamable HTTP)
           ▼
┌──────────────────────┐
│  MCP Server (TS)     │   Translates intent into API calls.
│  kandidat-mcp        │   Knows the domain vocabulary.
│                      │   Never touches the database directly.
└──────────┬───────────┘
           │ HTTP/JSON calls
           ▼
┌──────────────────────┐
│  kandidat API        │   All business rules enforced here.
│  Flask /api/*        │   Pydantic validation, state machine,
│                      │   cascade deletes, enum checks.
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PostgreSQL / SQLite │   Source of truth.
└──────────────────────┘
```

### The key principle

> The MCP server is a **semantic proxy**: it adds zero business logic.
> Every validation, constraint, and side-effect stays in the Flask API.
> The MCP server's only job is to expose **rich descriptions** so the LLM
> understands what it can do and what each field means.

This means:
- **No migration risk**: the MCP server can't corrupt data, because it goes through the same
  validation as the web UI.
- **No duplication**: business rules live in one place (Flask services).
- **Easy to remove**: if MCP doesn't work out, you delete one folder. kandidat is unchanged.

------

## 🎯 2. What is MCP and Why

### MCP in 30 seconds

MCP (Model Context Protocol) is a standard that lets an LLM call external tools through a
well-defined contract. Think of it like OpenAPI, but designed for AI agents instead of humans.

An MCP server exposes three things:

| Concept | What it is | kandidat example |
|---------|-----------|------------------|
| **Tools** | Functions the LLM can call | `create_candidature`, `list_cibles` |
| **Resources** | Read-only data the LLM loads into context | Enum values, state machine rules |
| **Prompts** | Pre-built prompt templates | "Fais le point sur mes candidatures actives" |

### Why MCP instead of just calling the API directly?

| Approach | Problem |
|----------|---------|
| LLM calls REST API directly | The LLM has to guess URLs, HTTP methods, JSON structure. It hallucinates fields, sends wrong payloads, doesn't know enum values. |
| MCP server in front of API | The LLM sees typed tool definitions with descriptions, required fields, enum constraints. It knows exactly what's valid before calling. |

### Why TypeScript + streamable HTTP?

- **TypeScript**: The `@modelcontextprotocol/sdk` is the reference implementation, best maintained.
  The MCP server is thin (proxy only), so the language choice has minimal impact on your stack.
- **Streamable HTTP**: The modern MCP transport. Works over standard HTTP, supports streaming
  responses (useful for long LLM operations like CV adaptation), and is compatible with both
  Claude Desktop and Claude Code.

------

## 🏗️ 3. Current State of kandidat

### What already exists (and is good)

Your API layer (`/api/*`) is **well-suited for MCP integration**. Specifically:

1. **Complete REST coverage**: Every entity (candidature, cible, contact, fichier, setting)
   has CRUD endpoints returning JSON.
2. **Pydantic validation**: Input schemas exist for create/update operations.
3. **Consistent response format**: All endpoints return `{"data": ...}` or `{"error": "..."}`.
4. **Status machine enforcement**: Transitions are validated server-side.

### Data model summary

```text
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐
│   Cible     │1────N │ Candidature  │1────N │    Fichier       │
│ id, nom     │       │ slug (PK)    │       │ id, nom, chemin  │
│ categorie   │       │ entreprise   │       └──────────────────┘
│ contactee   │       │ poste, type  │
│ url, desc   │       │ statut ◄──── state machine
│ email       │       │ priorite     │       ┌──────────────────┐
│ linkedin    │       │ cible_id(FK) │1────N │HistoriqueStatut  │
└──────┬──────┘       │ contenu      │       │ ancien/nouveau   │
       │1────N        └──────────────┘       │ date, commentaire│
┌──────┴──────┐                              └──────────────────┘
│  Contact    │       ┌──────────────┐
│ nom, prenom │       │   Setting    │
│ email, tel  │       │ key: value   │  (LLM config, CV ref, Tavily)
│ linkedin    │       └──────────────┘
│ fonction    │
└─────────────┘
```

### Enum values (the LLM needs to know these)

| Enum | Valid values |
|------|-------------|
| Statuts | `brouillon`, `envoyee`, `relancee`, `entretien`, `acceptee`, `refusee`, `sans-reponse`, `archivee` |
| Types | `offre`, `spontanee` |
| Priorites | `haute`, `moyenne`, `basse` |
| Categories candidature | `entreprise`, `esn`, `cabinet`, `groupe`, `organisation` |
| Categories cible | `grands-groupes`, `esn`, `entreprises`, `cabinets`, `organisations` |

### Status state machine

```text
brouillon ──► envoyee ──► relancee ──► entretien ──► acceptee ──► archivee
    │             │            │            │
    │             │            │            └──► refusee ──► archivee
    │             │            │
    │             │            └──► sans-reponse ──► archivee
    │             │
    │             └──► sans-reponse ──► archivee
    │
    └──► archivee
```

> **Rule**: `archivee` is terminal. No transition out. The LLM must understand this.

### Existing API endpoints

#### Candidatures

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `GET` | `/api/candidatures` | List all (filterable: statut, type, priorite, categorie) |
| `GET` | `/api/candidatures/<slug>` | Get one by slug |
| `POST` | `/api/candidatures` | Create new (JSON body) |
| `PUT` | `/api/candidatures/<slug>` | Partial update (Pydantic validated) |
| `DELETE` | `/api/candidatures/<slug>` | Delete + cascade files on disk |
| `GET` | `/api/candidatures/<slug>/historique` | Status change timeline |
| `PATCH` | `/api/candidatures/<slug>/historique/<id>` | Edit timeline comment |
| `POST` | `/api/candidatures/<slug>/fichiers` | Upload file (multipart) |
| `DELETE` | `/api/candidatures/<slug>/fichiers/<filename>` | Delete file |
| `GET` | `/api/candidatures/<slug>/fichiers/<filename>/download` | Download file |
| `POST` | `/api/candidatures/<slug>/cv/adapt` | Adapt CV via LLM |
| `POST` | `/api/candidatures/<slug>/cv/save` | Save adapted CV (PDF+DOCX) |
| `POST` | `/api/candidatures/<slug>/cv/convert` | Convert CV without LLM |

#### Cibles & Contacts

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `GET` | `/api/cibles` | List all grouped by category |
| `POST` | `/api/cibles` | Create target company |
| `PUT` | `/api/cibles/<id>` | Update target company |
| `DELETE` | `/api/cibles/<id>` | Delete (cascades to all candidatures!) |
| `POST` | `/api/cibles/reorder` | Reorder within category |
| `POST` | `/api/cibles/toggle` | Toggle contacted status |
| `GET` | `/api/cibles/<id>/detail` | Full detail + contacts + candidatures |
| `POST` | `/api/cibles/<id>/contacts` | Create contact |
| `PUT` | `/api/cibles/<id>/contacts/<cid>` | Update contact |
| `DELETE` | `/api/cibles/<id>/contacts/<cid>` | Delete contact |
| `POST` | `/api/cibles/<id>/enrich` | AI enrichment (Tavily + LLM) |
| `POST` | `/api/cibles/<id>/enrich/apply` | Apply enrichment suggestions |

#### Search, Stats, Dashboard

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `GET` | `/api/search?q=` | Full-text search |
| `GET` | `/api/stats` | Dashboard statistics |
| `POST` | `/api/dashboard/regenerate` | Regenerate Obsidian dashboard |

#### Settings

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `GET` | `/api/settings` | All settings (sensitive values masked) |
| `GET` | `/api/settings/cv-reference` | CV reference HTML content |
| `PUT` | `/api/settings/cv-reference` | Upload CV reference (multipart) |
| `PUT` | `/api/settings/llm` | Configure LLM provider |
| `POST` | `/api/settings/llm/health` | Health check LLM |
| `GET` | `/api/settings/llm/models` | List Ollama models |
| `PUT` | `/api/settings/tavily` | Configure Tavily API key |
| `POST` | `/api/settings/tavily/health` | Health check Tavily |

------

## 🔌 4. Proposed Architecture

### High-level structure

```text
kandidat-mcp/                  # Separate project or monorepo subfolder
├── src/
│   ├── index.ts               # MCP server entry point (streamable HTTP)
│   ├── client.ts              # HTTP client wrapper for kandidat API
│   ├── tools/
│   │   ├── candidatures.ts    # Tools: list, get, create, update, delete
│   │   ├── cibles.ts          # Tools: list, get, create, update, delete
│   │   ├── contacts.ts        # Tools: create, update, delete
│   │   ├── search.ts          # Tools: search, stats
│   │   └── ai-operations.ts   # Tools: enrich, adapt CV
│   ├── resources/
│   │   └── enums.ts           # Resources: static enum values, state machine
│   └── prompts/
│       └── templates.ts       # Pre-built prompt templates
├── package.json
├── tsconfig.json
└── .env.example               # KANDIDAT_API_URL=http://localhost:8000
```

### Design decisions

| Decision | Rationale |
|----------|-----------|
| **Separate project** (not inside kandidat) | Different runtime (Node/TS vs Python), different deploy cycle. Keeps kandidat clean. |
| **One HTTP client, shared** | All tools call the same base URL. Central error handling, timeout, retries. |
| **Tools grouped by domain** | Easier to navigate. Each file registers its tools with the MCP server. |
| **Resources for enums** | The LLM loads these automatically. No need to call a tool just to know valid statuses. |
| **No authentication (v1)** | kandidat API has no auth. MCP server runs locally alongside the API. If auth is added later, the client.ts wrapper handles it in one place. |

### What the MCP server does NOT do

- **No database access**: Everything goes through `/api/*`.
- **No file system access**: File uploads go through the API's multipart endpoint.
- **No business logic**: No status validation, no slug generation, no cascade logic.
- **No caching**: The API is the single source of truth. Every tool call hits the API fresh.

------

## 🛠️ 5. Complete Tool Catalog

### How to read this catalog

Each tool is described with:
- **Name**: What the LLM sees (snake_case, verb first)
- **Purpose**: Natural language description the LLM reads to decide when to use this tool
- **Inputs**: What the LLM must provide (required vs optional)
- **API call**: What HTTP request the MCP server makes under the hood
- **Annotations**: MCP metadata that tells the LLM client about safety

### Annotations explained

| Annotation | Meaning |
|------------|---------|
| `readOnlyHint: true` | This tool only reads data. Safe to call anytime. |
| `destructiveHint: true` | This tool deletes or permanently modifies data. Client should confirm with user. |
| `idempotentHint: true` | Calling this tool twice with the same input produces the same result (safe to retry). |

------

### 5.1 READ Tools (Tier 1 — implement first, zero risk)

These tools are safe, idempotent, and read-only. They let the LLM understand the current
state of your job search before taking any action.

------

#### `list_candidatures`

> **Purpose**: "List all job applications with optional filters by status, type, priority, or company category. Returns an array of applications with their key fields."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `statut` | string | no | Filter: `brouillon`, `envoyee`, `relancee`, `entretien`, `acceptee`, `refusee`, `sans-reponse`, `archivee` |
| `type` | string | no | Filter: `offre`, `spontanee` |
| `priorite` | string | no | Filter: `haute`, `moyenne`, `basse` |
| `categorie` | string | no | Filter: `entreprise`, `esn`, `cabinet`, `groupe`, `organisation` |

**API call**: `GET /api/candidatures?statut=X&type=Y&priorite=Z&categorie=W`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

**Example LLM usage**: "Montre-moi toutes mes candidatures en attente d'entretien"
→ calls `list_candidatures({ statut: "entretien" })`

------

#### `get_candidature`

> **Purpose**: "Get complete details of a specific job application by its slug identifier, including attached files, company info, status, dates, and content."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Kebab-case identifier (e.g. `datadog`, `ovh-cloud`) |

**API call**: `GET /api/candidatures/<slug>`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

#### `get_candidature_history`

> **Purpose**: "Get the status change timeline for a job application: every transition with its date, previous status, new status, and optional comment."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Candidature identifier |

**API call**: `GET /api/candidatures/<slug>/historique`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

#### `list_cibles`

> **Purpose**: "List all target companies grouped by category (grands-groupes, esn, entreprises, cabinets, organisations). Each entry includes name, contacted status, and count of active applications."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | — | — | — |

**API call**: `GET /api/cibles`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

#### `get_cible_detail`

> **Purpose**: "Get a target company's full details: name, category, website, description, contacts list, and all linked active job applications."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |

**API call**: `GET /api/cibles/<cible_id>/detail`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

#### `search_candidatures`

> **Purpose**: "Full-text search across all job applications. Searches company name, position, content, and attached file names."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | **yes** | Search terms |

**API call**: `GET /api/search?q=<query>`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

#### `get_stats`

> **Purpose**: "Get dashboard statistics: total application count, breakdowns by status/type/priority/category, and chronological timeline of applications."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | — | — | — |

**API call**: `GET /api/stats`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

#### `get_settings`

> **Purpose**: "Get current application settings: which LLM provider is configured, whether a CV reference exists, Tavily API status."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | — | — | — |

**API call**: `GET /api/settings`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: true }`

------

### 5.2 WRITE Tools (Tier 2 — creation & updates)

These tools create or modify data. They are **not destructive** (they don't delete anything),
but they do change state. The API enforces all validation.

------

#### `create_cible`

> **Purpose**: "Add a new target company to track. You must specify a name and category. The company will be added to the bottom of its category list."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `nom` | string | **yes** | Company name |
| `categorie` | string | **yes** | One of: `grands-groupes`, `esn`, `entreprises`, `cabinets`, `organisations` |
| `url` | string | no | Company website URL |
| `description` | string | no | Short description of the company |
| `email` | string | no | General contact email |
| `linkedin` | string | no | LinkedIn company page URL |

**API call**: `POST /api/cibles`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: false }`

> **Why not idempotent**: Calling twice with the same name+category will fail (unique constraint)
> or create a duplicate if names differ slightly. The LLM should check `list_cibles` first.

------

#### `create_candidature`

> **Purpose**: "Create a new job application linked to an existing target company. The application starts in 'brouillon' status. The company's category determines the candidature's company category automatically. You must provide a valid cible_id — use list_cibles or get_cible_detail first to find it."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `entreprise` | string | **yes** | Company name (will become the slug in kebab-case) |
| `poste` | string | no | Job title |
| `type` | string | no | `offre` (default) or `spontanee` |
| `localisation` | string | no | Job location |
| `priorite` | string | no | `haute`, `moyenne` (default), or `basse` |
| `cible_id` | integer | **yes** | ID of the target company (must exist) |
| `contenu` | string | no | Markdown content: job description, notes, URL |

**API call**: `POST /api/candidatures`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: false }`

> **Important side-effects**:
> - Slug is auto-generated from `entreprise` (kebab-case, accents stripped)
> - `categorie_entreprise` is derived from the cible's category (automatic mapping)
> - `date_candidature` is set to today
> - Status is always `brouillon`
> - The cible is automatically marked as `contactee`
> - A directory is created on disk for future files

------

#### `update_candidature`

> **Purpose**: "Update one or more fields on an existing job application. You can change status (must follow the state machine), priority, dates, content, etc. If changing status, you can optionally include a comment explaining the transition."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Candidature identifier |
| `statut` | string | no | New status (must be a valid transition from current) |
| `priorite` | string | no | `haute`, `moyenne`, `basse` |
| `categorie_entreprise` | string | no | Company category override |
| `date_candidature` | string | no | Date in `YYYY-MM-DD` format |
| `date_relance` | string | no | Follow-up date in `YYYY-MM-DD` format |
| `entreprise` | string | no | Company name |
| `poste` | string | no | Job title |
| `type` | string | no | `offre` or `spontanee` |
| `localisation` | string | no | Location |
| `contenu` | string | no | Markdown content |
| `commentaire` | string | no | Comment for status change (ignored if status unchanged) |

**API call**: `PUT /api/candidatures/<slug>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: true }`

> **Status machine enforced**: If you try `brouillon -> entretien`, the API returns 400.
> The LLM must follow: `brouillon -> envoyee -> relancee -> entretien`.

> **Gap identified**: The current API endpoint does **not** accept `commentaire` in the JSON
> body. This field is only handled by the web form route. **Must be fixed before MCP** (see
> section 6).

------

#### `update_cible`

> **Purpose**: "Update a target company's information: name, category, website, description, email, or LinkedIn URL."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |
| `nom` | string | no | New company name |
| `categorie` | string | no | New category |
| `url` | string | no | Website URL |
| `description` | string | no | Description |
| `email` | string | no | Contact email |
| `linkedin` | string | no | LinkedIn URL |

**API call**: `PUT /api/cibles/<cible_id>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: true }`

------

#### `create_contact`

> **Purpose**: "Add a contact person (recruiter, hiring manager, CTO...) to a target company."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |
| `nom` | string | **yes** | Last name |
| `prenom` | string | no | First name |
| `email` | string | no | Email address |
| `telephone` | string | no | Phone number |
| `linkedin` | string | no | LinkedIn profile URL |
| `fonction` | string | no | Job title / role |

**API call**: `POST /api/cibles/<cible_id>/contacts`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: false }`

------

#### `update_contact`

> **Purpose**: "Update a contact's information for a target company."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |
| `contact_id` | integer | **yes** | Contact ID |
| `nom` | string | no | Last name |
| `prenom` | string | no | First name |
| `email` | string | no | Email |
| `telephone` | string | no | Phone |
| `linkedin` | string | no | LinkedIn URL |
| `fonction` | string | no | Job title |

**API call**: `PUT /api/cibles/<cible_id>/contacts/<contact_id>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: true }`

------

#### `update_historique_comment`

> **Purpose**: "Add or edit a comment on a specific status change in a candidature's history timeline."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Candidature identifier |
| `historique_id` | integer | **yes** | History entry ID |
| `commentaire` | string | **yes** | Comment text (max 1000 chars) |

**API call**: `PATCH /api/candidatures/<slug>/historique/<historique_id>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: true }`

------

### 5.3 DELETE Tools (Tier 3 — destructive, confirmation required)

These tools permanently delete data. The MCP annotations signal to the client that it
**must ask the user for confirmation** before executing.

------

#### `delete_candidature`

> **Purpose**: "Permanently delete a job application and all its attached files from disk. This cannot be undone. The target company will be marked as 'not contacted' if this was its last active application."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Candidature identifier |

**API call**: `DELETE /api/candidatures/<slug>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: true, idempotentHint: true }`

------

#### `delete_cible`

> **Purpose**: "Delete a target company AND ALL its linked job applications and files. This cascades and cannot be undone. Use with extreme caution."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |

**API call**: `DELETE /api/cibles/<cible_id>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: true, idempotentHint: true }`

> **Danger**: This is the most destructive operation in kandidat. Deleting a cible with
> 10 candidatures deletes all 10 + their files. The tool description must make this crystal
> clear to the LLM.

------

#### `delete_contact`

> **Purpose**: "Delete a contact from a target company. Only removes the contact, not the company or its applications."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |
| `contact_id` | integer | **yes** | Contact ID |

**API call**: `DELETE /api/cibles/<cible_id>/contacts/<contact_id>`

**Annotations**: `{ readOnlyHint: false, destructiveHint: true, idempotentHint: true }`

------

### 5.4 AI Operation Tools (Tier 4 — LLM-powered features)

These tools trigger AI operations (web search, LLM calls). They may be slow (10-30s)
and consume API credits.

------

#### `enrich_cible`

> **Purpose**: "Trigger AI-powered enrichment for a target company: searches the web for company info (website, LinkedIn, sector) and contacts (leadership, team members), then returns suggestions. Does NOT modify the company — you must use apply_enrichment to save changes."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |

**API call**: `POST /api/cibles/<cible_id>/enrich`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: false }`

> Read-only because it returns suggestions without modifying anything.

------

#### `apply_enrichment`

> **Purpose**: "Apply selected enrichment suggestions to update a target company's information and optionally create new contacts. Takes the output from enrich_cible and applies the fields you want to keep."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `cible_id` | integer | **yes** | Target company ID |
| `accepted` | object | **yes** | Selected fields/contacts from enrichment result |

**API call**: `POST /api/cibles/<cible_id>/enrich/apply`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: false }`

------

#### `adapt_cv`

> **Purpose**: "Generate an AI-adapted version of your CV for a specific job application. Uses the configured LLM to tailor the CV based on the job posting content. Returns HTML — use save_adapted_cv to persist as PDF+DOCX."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Candidature identifier |
| `cv_source` | string | no | `auto` (default), `global`, or `candidature` |

**API call**: `POST /api/candidatures/<slug>/cv/adapt`

**Annotations**: `{ readOnlyHint: true, destructiveHint: false, idempotentHint: false }`

------

#### `save_adapted_cv`

> **Purpose**: "Save an adapted CV as PDF and DOCX files attached to the job application. Takes the HTML output from adapt_cv."

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **yes** | Candidature identifier |
| `adapted_html` | string | **yes** | HTML content from adapt_cv result |

**API call**: `POST /api/candidatures/<slug>/cv/save`

**Annotations**: `{ readOnlyHint: false, destructiveHint: false, idempotentHint: false }`

------

### 5.5 MCP Resources (loaded into LLM context automatically)

Resources are different from tools: they are **loaded once** into the LLM's context window
when the conversation starts. The LLM doesn't need to "call" them — it just knows the data.

| Resource URI | Content | Why |
|-------------|---------|-----|
| `kandidat://enums/statuts` | `["brouillon", "envoyee", ...]` | LLM always knows valid statuses |
| `kandidat://enums/types` | `["offre", "spontanee"]` | LLM never guesses wrong |
| `kandidat://enums/priorites` | `["haute", "moyenne", "basse"]` | — |
| `kandidat://enums/categories-cible` | `["grands-groupes", "esn", ...]` | — |
| `kandidat://enums/categories-candidature` | `["entreprise", "esn", ...]` | — |
| `kandidat://rules/status-transitions` | JSON map of allowed transitions | LLM plans multi-step status changes correctly |
| `kandidat://rules/cible-to-candidature-mapping` | `{"grands-groupes": "groupe", ...}` | LLM understands the automatic derivation |

> **Decision for you**: Resources consume context window tokens. The enums above total ~500
> tokens — negligible. But if you wanted to expose the full settings or CV reference as
> resources, that would be expensive. Keep resources small and static.

------

### 5.6 MCP Prompts (optional, pre-built templates)

Prompts are templates the user can trigger from the client UI. They save typing for
common workflows.

| Prompt name | Template | What it does |
|-------------|----------|-------------|
| `status_report` | "Give me a summary of all my active job applications, grouped by status" | Calls `get_stats` + `list_candidatures` and summarizes |
| `new_application` | "Create an application at {company} for the position of {position}" | Guides the LLM through: find/create cible → create candidature |
| `follow_up_check` | "Which applications need a follow-up? (sent more than 7 days ago, not yet followed up)" | Calls `list_candidatures(statut=envoyee)` and filters by date |

> These are convenience features. Not required for v1. Can be added later.

------

## ⚠️ 6. Gaps to Fill Before Building

### 6.1 API changes required (in kandidat Flask backend)

#### Gap 1: `GET /api/enums` endpoint (PRIORITY: HIGH)

**Problem**: The LLM needs to know valid enum values. Currently, these are hardcoded in
Python constants. The MCP server would have to hardcode them too, creating duplication that
drifts over time.

**Solution**: Create a new endpoint that returns all enums and the state machine:

```json
GET /api/enums
{
  "data": {
    "statuts": ["brouillon", "envoyee", ...],
    "types": ["offre", "spontanee"],
    "priorites": ["haute", "moyenne", "basse"],
    "categories_candidature": ["entreprise", "esn", ...],
    "categories_cible": ["grands-groupes", "esn", ...],
    "status_transitions": {
      "brouillon": ["envoyee", "archivee"],
      "envoyee": ["relancee", "sans-reponse", "archivee"],
      ...
    },
    "cible_to_candidature_mapping": {
      "grands-groupes": "groupe",
      ...
    }
  }
}
```

**Impact**: Small. One new read-only endpoint, ~20 lines of code.

**Why it matters**: Without this, the MCP server must hardcode the enums. If you add a new
status or category later, you have to update both the API and the MCP server. With this
endpoint, the MCP server can fetch enums dynamically and expose them as Resources.

------

#### Gap 2: `commentaire` field in PUT candidatures API (PRIORITY: HIGH)

**Problem**: When changing a candidature's status via the web UI, users can add a comment
explaining the transition (e.g., "Entretien prevu le 20 mars"). This comment is stored in
`historique_statuts`. However, the `PUT /api/candidatures/<slug>` endpoint ignores the
`commentaire` field — it only works through the web form route.

**Current behavior**:
```python
# In api/candidatures.py, line 136:
update_candidature(slug, fields)  # <-- no commentaire parameter!

# But the service supports it:
def update_candidature(slug, fields, commentaire=None):  # <-- parameter exists
```

**Solution**: Read `commentaire` from the JSON body and pass it through:

```python
commentaire = data.get("commentaire")
update_candidature(slug, fields, commentaire=commentaire)
```

**Impact**: 2-line change. No schema modification needed (commentaire is not a candidature
field, it's metadata for the status transition).

------

#### Gap 3: Missing Pydantic validators (PRIORITY: MEDIUM)

Several fields accept free-form strings where they should validate format:

| Schema | Field | Missing validation |
|--------|-------|--------------------|
| `CandidatureCreate` | `type` | Should validate against `["offre", "spontanee"]` |
| `CandidatureCreate` | `priorite` | Should validate against `["haute", "moyenne", "basse"]` |
| `CandidatureUpdate` | `date_candidature` | Should validate `YYYY-MM-DD` format |
| `CandidatureUpdate` | `date_relance` | Should validate `YYYY-MM-DD` format |
| `CibleCreate` | `url` | No URL format validation |
| `CibleCreate` | `email` | No email format validation |
| `ContactCreate` | `email` | No email format validation |

**Impact**: The API already validates these downstream (in route handlers or service layer),
so this isn't a security issue. But adding Pydantic validators gives cleaner error messages
and catches bad input earlier — especially important when the caller is an LLM that may
hallucinate field values.

**Recommendation**: Fix `type`, `priorite`, `date_*` validators. Leave `url` and `email`
as free-form strings (too many edge cases with email/URL validation, and the current
behavior accepts empty strings intentionally).

------

### 6.2 Nice-to-have API additions (not blocking)

| Endpoint | Rationale | Priority |
|----------|-----------|----------|
| `GET /api/candidatures/<slug>/fichiers` | List files without loading the full candidature. Useful after upload to confirm. | Low |
| `GET /api/cibles/<id>` | Simple cible GET (without contacts/candidatures). The detail endpoint is heavier than needed for simple lookups. | Low |

------

## 🛡️ 7. What Needs Human Confirmation

The MCP protocol supports `destructiveHint` annotations that tell the client "ask the user
before executing this." Here's how this maps to kandidat operations:

### Always confirm (destructiveHint: true)

| Tool | Why |
|------|-----|
| `delete_candidature` | Deletes files on disk. Irreversible. |
| `delete_cible` | **Cascading delete**: removes all linked candidatures + files. Most dangerous operation. |
| `delete_contact` | Lower risk but still a delete. |

### Consider confirming (application-level, not MCP)

| Tool | Why |
|------|-----|
| `update_candidature` with `statut: archivee` | Terminal state. No way back. The LLM should warn "this candidature will be archived permanently." |
| `apply_enrichment` | Overwrites existing cible fields. The LLM should show current vs. suggested values. |
| `save_adapted_cv` | Creates files on disk. Low risk but consumes storage. |

### Never needs confirmation (readOnlyHint: true)

All READ tools, plus `enrich_cible` and `adapt_cv` (they return data without modifying anything).

------

## 📋 8. Implementation Plan

### Sequencing rationale

1. **API fixes first**: The MCP server depends on a complete API. Fix gaps before building.
2. **READ tools first**: They're safe, let you validate the architecture, and are immediately
   useful ("show me my applications").
3. **WRITE tools second**: Once reads work, adds work.
4. **DELETE and AI tools last**: Higher risk, more complex to test.

------

### Phase 1 — API prerequisites

| Step | Task | Complexity | Files touched |
|------|------|------------|---------------|
| 1.1 | Create `GET /api/enums` endpoint | S | `api/other_routes.py` |
| 1.2 | Pass `commentaire` through `PUT /api/candidatures/<slug>` | S | `api/candidatures.py` (2 lines) |
| 1.3 | Add Pydantic validators for `type`, `priorite`, `date_*` | S | `services/schemas.py` |

**Total**: ~1 hour of work. All changes are backward-compatible.

------

### Phase 2 — MCP Server scaffold + READ tools

| Step | Task | Complexity | Notes |
|------|------|------------|-------|
| 2.1 | Init TypeScript project with `@modelcontextprotocol/sdk` | S | `pnpm create`, tsconfig, .env |
| 2.2 | Build HTTP client wrapper (`client.ts`) | S | Base URL, error handling, timeout |
| 2.3 | Implement 8 READ tools | M | Mostly boilerplate: parse input → HTTP GET → return data |
| 2.4 | Implement enum Resources (fetch from `/api/enums`) | S | Loaded once at startup |
| 2.5 | Test with MCP Inspector / Claude Desktop | S | Manual smoke test |

**Total**: ~half a day. After this, Claude can already read your full job search data.

------

### Phase 3 — WRITE tools

| Step | Task | Complexity | Notes |
|------|------|------------|-------|
| 3.1 | Implement `create_cible` + `create_candidature` | M | The two main creation flows |
| 3.2 | Implement `update_candidature` + `update_cible` | M | Partial update with validation |
| 3.3 | Implement `create_contact` + `update_contact` + `update_historique_comment` | S | Straightforward |
| 3.4 | Add MCP annotations on all tools | S | Metadata only |

**Total**: ~half a day. After this, Claude can create and manage your entire job search.

------

### Phase 4 — DELETE + AI tools

| Step | Task | Complexity | Notes |
|------|------|------------|-------|
| 4.1 | Implement 3 delete tools with `destructiveHint: true` | S | Simple API passthrough |
| 4.2 | Implement `enrich_cible` + `apply_enrichment` | M | Needs structured `accepted` payload |
| 4.3 | Implement `adapt_cv` + `save_adapted_cv` | M | Large HTML payloads, may need streaming |

**Total**: ~half a day.

------

### Phase 5 — Polish (optional)

| Step | Task | Complexity | Notes |
|------|------|------------|-------|
| 5.1 | Add MCP Prompts (status_report, new_application, follow_up_check) | S | Templates only |
| 5.2 | Add `Dockerfile` for the MCP server | S | If deploying alongside kandidat |
| 5.3 | Integration tests (MCP server → real kandidat API) | M | End-to-end validation |

------

### Visual timeline

```text
Phase 1 (API fixes)     ████               ~1h
Phase 2 (READ tools)    ████████████       ~4h
Phase 3 (WRITE tools)   ████████████       ~4h
Phase 4 (DELETE + AI)    ████████████       ~4h
Phase 5 (Polish)         ██████             ~2h
                         ─────────────────
                         Total: ~2 days of focused work
```

------

## ❓ 9. Open Questions for You

These are decisions that affect the architecture. I need your input before proceeding.

### Q1: Separate repo or subfolder?

| Option | Pros | Cons |
|--------|------|------|
| **`kandidat-mcp/`** as a separate repo | Clean separation, independent versioning, independent CI | Two repos to maintain |
| **`mcp/`** subfolder inside kandidat | Single repo, easier to keep in sync, one CI pipeline | Mixes Python and TypeScript, heavier repo |

> **My recommendation**: Subfolder `mcp/` inside kandidat. The MCP server is tightly coupled
> to kandidat's API contract. Keeping them together makes it easier to detect breaking changes.

### Q2: Should delete tools be exposed at all?

You might decide that deleting candidatures/cibles should only be done through the web UI,
never through an LLM. This would reduce risk at the cost of convenience.

> **My recommendation**: Expose them with `destructiveHint: true`. The Claude client will
> always ask for confirmation. And the API already validates everything.

### Q3: Should the MCP server run on dockhost alongside kandidat?

| Option | How it works |
|--------|-------------|
| **Local only** | MCP server runs on your machine, calls kandidat API (localhost or dockhost). Claude Desktop/Code connects locally. |
| **Deployed on dockhost** | MCP server runs as a container next to kandidat. Accessible remotely. |

> **My recommendation**: Start local-only. An MCP server for a personal tool doesn't need
> to be deployed. If you later want remote access, add a Docker deployment.

### Q4: Tavily and LLM settings management via MCP?

Should the MCP server expose tools to configure LLM providers and API keys? This would
let you say "Switch to Claude as LLM provider" via natural language.

> **My recommendation**: No for v1. Settings are rarely changed and involve API keys.
> Keep settings management in the web UI. The `get_settings` READ tool is enough for the
> LLM to know what's configured.

------

## 📚 10. Glossary

| Term | Definition |
|------|-----------|
| **MCP** | Model Context Protocol — standard for LLM tool integration |
| **Tool** | A function the LLM can call (with typed inputs and outputs) |
| **Resource** | Read-only data loaded into LLM context (like enum values) |
| **Prompt** | Pre-built template for common workflows |
| **Cible** | Target company being tracked for job applications |
| **Candidature** | A job application linked to a cible |
| **Slug** | Kebab-case identifier derived from company name (e.g., `ovh-cloud`) |
| **Streamable HTTP** | MCP transport protocol over standard HTTP with streaming support |
| **destructiveHint** | MCP annotation telling the client to confirm before executing |

------

> **Document created on**: 2026-03-16
> **Author**: Claude (analysis), Xavier Gueret (review)
> **Version**: 1.0-draft
