"""LLM provider abstraction layer with Protocol pattern."""

from typing import Protocol

from services.settings import get_setting


class LLMProvider(Protocol):
    """Protocol for LLM providers. Implement complete, adapt_cv and health_check."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send system+user prompts to the LLM, return text response."""
        ...

    def adapt_cv(self, cv_html: str, system_prompt: str, user_prompt: str) -> str:
        """Send CV and prompts to the LLM, return adapted HTML string."""
        ...

    def health_check(self) -> dict:
        """Test connectivity to the provider. Returns {"status": "ok", ...} or raises."""
        ...


def get_provider() -> LLMProvider:
    """Factory: return the configured LLM provider instance.

    Raises ValueError if no provider is configured or provider is unknown.
    """
    provider_name = get_setting("llm_provider")
    if not provider_name:
        raise ValueError("Aucun fournisseur LLM configure. Configurez-le dans les parametres.")

    if provider_name == "ollama":
        from services.llm.ollama import OllamaProvider

        url = get_setting("llm_ollama_url") or "http://localhost:11434"
        model = get_setting("llm_ollama_model") or "llama3.2"
        return OllamaProvider(url=url, model=model)

    if provider_name == "claude":
        from services.llm.claude import ClaudeProvider

        api_key = get_setting("llm_claude_api_key")
        if not api_key:
            raise ValueError("Cle API Claude non configuree")
        model = get_setting("llm_claude_model") or "claude-sonnet-4-20250514"
        return ClaudeProvider(api_key=api_key, model=model)

    raise ValueError(f"Fournisseur LLM inconnu : {provider_name}")
