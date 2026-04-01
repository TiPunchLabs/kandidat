# ADR-006: Settings as a key-value store in the database

## Status

Accepted

## Context

kandidat needs runtime-configurable settings for LLM provider selection (provider name, URL, model, API key), CV reference storage, prompt customization (CV adapt, match scoring), and external API keys (Tavily). These settings must persist across restarts and be editable from the UI without redeploying.

## Decision

Use a `Setting` model with a simple key-value schema:
- `key` (String, primary key)
- `value` (Text)
- `updated_at` (String, ISO 8601 timestamp)

The `services/settings.py` module provides a minimal CRUD API: `get_setting(key)`, `set_setting(key, value)`, `get_all_settings()`, plus domain helpers like `upload_cv_reference(html)` and `get_cv_reference_html()`.

Known keys include: `llm_provider`, `llm_ollama_url`, `llm_ollama_model`, `llm_claude_api_key`, `llm_claude_model`, `cv_reference_html`, `cv_reference_date`, `cv_adapt_system_prompt`, `cv_adapt_user_prompt`, `match_system_prompt`, `match_user_prompt`, `tavily_api_key`.

The settings page (`templates/settings.html`) provides a form-based UI for all configuration.

## Consequences

- Adding a new setting requires no schema migration -- just use a new key.
- No type safety at the storage level; all values are strings. Type conversion happens in consumers (e.g. `get_provider()` interprets the provider name).
- The CV reference HTML is stored as a setting value, which can be large. This is acceptable for a single-user application.
- No built-in validation of setting keys -- any string can be stored. Validation is the responsibility of the consuming service.
- Settings are read from the database on every access (no caching), which is fine for low-traffic single-user usage.
