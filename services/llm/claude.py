"""Claude LLM provider — communicates via Anthropic SDK."""

import logging

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60
MAX_TOKENS = 8192


class ClaudeProvider:
    """Claude provider using the Anthropic Python SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic

        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send system+user prompts to Claude, return text response."""
        import anthropic

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=TIMEOUT_SECONDS,
            )
        except anthropic.APIConnectionError:
            raise ConnectionError("Impossible de se connecter a l'API Claude")
        except anthropic.AuthenticationError:
            raise ConnectionError("Cle API Claude invalide")
        except anthropic.APITimeoutError:
            raise TimeoutError(f"Claude n'a pas repondu dans les {TIMEOUT_SECONDS}s")
        except anthropic.APIStatusError as e:
            raise ConnectionError(f"Erreur Claude: {e.status_code} {e.message}")

        return response.content[0].text

    def adapt_cv(self, cv_html: str, system_prompt: str, user_prompt: str) -> str:
        """Send CV adaptation request to Claude and return the adapted HTML."""
        return self.complete(system_prompt, user_prompt)

    def health_check(self) -> dict:
        """Test connectivity to Claude API by counting tokens on a minimal message."""
        import anthropic

        try:
            self.client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
            )
        except anthropic.AuthenticationError:
            raise ConnectionError("Fournisseur LLM non accessible: cle API invalide")
        except anthropic.APIConnectionError:
            raise ConnectionError("Fournisseur LLM non accessible: impossible de se connecter a l'API Claude")
        except anthropic.APIStatusError as e:
            raise ConnectionError(f"Fournisseur LLM non accessible: {e.message}")

        return {"provider": "claude", "status": "ok", "model": self.model}
