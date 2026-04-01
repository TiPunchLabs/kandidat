# Quickstart

Get kandidat running in under 5 minutes.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## 1. Install dependencies

```bash
uv sync
```

## 2. Start the server

```bash
uv run python main.py
```

Open <http://localhost:8000> in a browser. kandidat runs on SQLite by default — no database setup needed.

## 3. Create your first application

1. Click **Nouvelle** in the sidebar
2. Fill in the company name and job title
3. Click **Creer** — you land on the application detail page

## 4. Configure your CV reference (recommended)

A reference CV unlocks two AI features: **CV adaptation** and **match scoring**.

1. Go to **Parametres** (sidebar)
2. In the **CV de reference** section, upload your CV (markdown format)
3. Save

## 5. Configure an LLM provider (optional)

AI features (CV adaptation, match scoring, company enrichment) require an LLM provider.

**Option A — Ollama (local, free)**

1. [Install Ollama](https://ollama.ai) and pull a model (see recommendations below)
2. In **Parametres**, set provider to **Ollama**, verify the URL and select your model

### Recommended Ollama models

kandidat relies on three AI capabilities with different requirements:

| Feature | Requirement | Description |
| --- | --- | --- |
| **CV adaptation** | Fluent French + structured HTML output | Rewrites your CV to match a job offer |
| **Match scoring** | Analysis + JSON structured output | Scores CV/offer fit with detailed feedback |
| **Company enrichment** | Extraction + JSON structured output | Structures raw web search results |

**Best picks by hardware:**

| Model | VRAM | CV adapt | Match | Enrichment | Notes |
| --- | --- | --- | --- | --- | --- |
| `qwen2.5:7b` | ~5 GB | Good | Good | Good | Best balance for most setups. Default choice. |
| `qwen2.5:14b` | ~9 GB | Very good | Very good | Very good | Step up if you have the VRAM. |
| `mistral-small:22b` | ~14 GB | Very good | Very good | Very good | Excellent French, strong structured output. |
| `gemma3:12b` | ~8 GB | Good | Good | Good | Solid alternative to Qwen 14B. |
| `llama3.1:8b` | ~5 GB | Decent | Good | Good | Weaker French than Qwen/Mistral. |
| `deepseek-r1:14b` | ~9 GB | Decent | Very good | Good | Strong reasoning, slower (chain-of-thought). |

> All three features need the model to output structured content (HTML or JSON). Models under 7B tend to produce malformed output and are not recommended.

```bash
# Example: install the default recommended model
ollama pull qwen2.5:7b

# Or if you have 16+ GB VRAM
ollama pull mistral-small:22b
```

**Option B — Claude API (distant)**

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
2. In **Parametres**, set provider to **Claude**, paste your API key

## 6. Try the AI features

### Match scoring

On any application detail page, click **Evaluer le match** to get a compatibility score (0-100%) with strengths, weaknesses, and missing skills.

> Requires: CV reference configured + LLM provider configured.

### CV adaptation

On any application detail page, click **Adapter mon CV** to generate a tailored CV based on the job description. Preview in HTML, then save as PDF and DOCX.

> Requires: CV reference configured + LLM provider configured.

### Company enrichment

On any company detail page, click **Enrichir via IA** to automatically find company info (website, LinkedIn, description) and contacts via web search.

> Requires: LLM provider configured + [Tavily](https://tavily.com) API key in Parametres.

## What's next

- Read the full [README](README.md) for Docker setup, MCP server, PostgreSQL, and deployment
- Explore the REST API documentation at `/docs` (Swagger UI)
- Use the [MCP server](README.md#mcp-server-llm-agent-integration) to manage kandidat from Claude Desktop or Claude Code
