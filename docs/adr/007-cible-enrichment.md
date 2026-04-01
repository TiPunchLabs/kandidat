# ADR-007: Cible enrichment via Tavily web search and LLM extraction

## Status

Accepted

## Context

When preparing job applications, users need company information (website, LinkedIn, description) and contact details (leadership, hiring managers). Manually researching each company is time-consuming. The application already has an LLM integration for other features.

## Decision

Implement a two-stage enrichment pipeline in `services/cible_enricher.py`:

1. **Web search (Tavily)**: Two targeted queries per company:
   - Company info: `"{company_name} site officiel linkedin"` (5 results, basic depth).
   - Contacts: `"{company_name} contacts dirigeants equipe linkedin"` (5 results, basic depth).
   Search results are formatted as text blocks with title, URL, and content snippet.

2. **LLM extraction**: The search results are sent to the LLM via `provider.complete()` with a system prompt requesting structured JSON output: `{"company": {url, linkedin, description, email}, "contacts": [{nom, prenom, fonction, linkedin, email, telephone}]}`.

3. **User review**: The enrichment results are returned as suggestions, not auto-applied. A preview page shows current vs. suggested values with checkboxes. The user selects which suggestions to accept.

4. **Apply**: `apply_enrichment()` updates the Cible fields and creates Contact records only for user-accepted suggestions.

The Tavily API key is stored as a setting (`tavily_api_key`).

## Consequences

- Enrichment quality depends on Tavily search results and LLM extraction accuracy.
- The user-review step prevents bad data from being blindly applied.
- Tavily is a paid API with usage limits; each enrichment consumes 2 search queries.
- Contact data found via web search may be outdated or incorrect -- the user bears responsibility for verification.
- If Tavily is unreachable or the API key is missing, the feature fails gracefully with a clear error message.
