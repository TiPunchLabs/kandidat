# ADR-002: LLM provider abstraction with Protocol pattern and factory

## Status

Accepted

## Context

kandidat uses LLM capabilities in three features: CV adaptation, match scoring, and cible enrichment. The project needs to support both a local LLM (Ollama) for offline/free usage and a cloud LLM (Claude via Anthropic SDK) for higher quality. The active provider and its configuration (URL, model, API key) must be switchable at runtime by the user through the settings page.

## Decision

Define an `LLMProvider` Protocol in `services/llm/__init__.py` with three methods:
- `complete(system_prompt, user_prompt) -> str` -- generic text completion (used by match scoring and enrichment).
- `adapt_cv(cv_html, system_prompt, user_prompt) -> str` -- CV-specific adaptation returning HTML.
- `health_check() -> dict` -- connectivity test.

A `get_provider()` factory function reads `llm_provider` from the Settings table and returns the appropriate concrete provider:
- `OllamaProvider` (`services/llm/ollama.py`) -- uses httpx to call the local Ollama API.
- `ClaudeProvider` (`services/llm/claude.py`) -- uses the `anthropic` SDK.

Provider configuration (URL, model, API key) is stored as settings and resolved at call time via lazy imports.

## Consequences

- Adding a new LLM provider requires only a new module implementing the Protocol and a branch in `get_provider()`.
- All three LLM features (CV adapt, match, enrichment) share the same provider and configuration -- no per-feature provider selection.
- The user can switch providers at runtime without restarting the server.
- No dependency injection framework is needed; Python's Protocol + factory pattern keeps it simple.
- Provider instantiation happens on every call (no singleton), which is acceptable given the low call frequency.
