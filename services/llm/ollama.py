"""Ollama LLM provider — communicates via OpenAI-compatible API."""

import logging

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120


class OllamaProvider:
    """Ollama provider using /v1/chat/completions endpoint."""

    def __init__(self, url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.url = url.rstrip("/")
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send system+user prompts to Ollama, return text response."""
        import httpx

        endpoint = f"{self.url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }

        try:
            response = httpx.post(endpoint, json=payload, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise TimeoutError(f"Ollama n'a pas repondu dans les {TIMEOUT_SECONDS}s. Essayez un modele plus rapide.")
        except httpx.ConnectError:
            raise ConnectionError(f"Impossible de se connecter a Ollama sur {self.url}")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"Erreur Ollama: {e.response.status_code} {e.response.text[:200]}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def adapt_cv(self, cv_html: str, system_prompt: str, user_prompt: str) -> str:
        """Send CV adaptation request to Ollama and return the adapted HTML."""
        return self.complete(system_prompt, user_prompt)

    def health_check(self) -> dict:
        """Test connectivity to Ollama server via GET /."""
        import httpx

        try:
            response = httpx.get(self.url, timeout=10)
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError(f"Fournisseur LLM non accessible: impossible de se connecter a {self.url}")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"Fournisseur LLM non accessible: {e.response.status_code}")

        return {"provider": "ollama", "status": "ok", "model": self.model}
