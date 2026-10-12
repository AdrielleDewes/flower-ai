"""Ollama adapter for the structured LLM provider contract."""

import json
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from app.config import OllamaConfig
from app.services.llm_provider import InvalidLLMOutputError, LLMProviderError


class OllamaProvider:
    """Request and validate structured responses from a local Ollama server."""

    def __init__(self, config: OllamaConfig) -> None:
        """Use explicit settings without connecting to Ollama yet."""
        self.config = config

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
    ) -> dict[str, Any]:
        """Convert Ollama's JSON message content to validated structured data."""
        request = Request(
            url=f"{self.config.base_url.rstrip('/')}/api/chat",
            data=json.dumps(
                {
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "format": schema.model_json_schema(),
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_body = response.read()
        except HTTPError as exc:
            if exc.code == 404:
                raise LLMProviderError(
                    f"Ollama model '{self.config.model}' is unavailable."
                ) from exc
            raise LLMProviderError(
                f"Ollama request failed with HTTP status {exc.code}."
            ) from exc
        except TimeoutError as exc:
            raise LLMProviderError("Ollama request timed out.") from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise LLMProviderError("Ollama request timed out.") from exc
            raise LLMProviderError("Could not connect to Ollama.") from exc
        except OSError as exc:
            raise LLMProviderError("Could not connect to Ollama.") from exc

        try:
            envelope = json.loads(response_body)
            if not isinstance(envelope, dict):
                raise TypeError("Ollama response must be an object.")
            if "error" in envelope:
                raise LLMProviderError("Ollama failed to generate a response.")

            message = envelope.get("message")
            if not isinstance(message, dict):
                raise TypeError("Ollama response has no message.")
            content = message.get("content")
            if not isinstance(content, str):
                raise TypeError("Ollama message has no content.")
            output = json.loads(content, parse_float=Decimal)
            validated = schema.model_validate(output)
        except (UnicodeDecodeError, TypeError, ValueError, ValidationError) as exc:
            raise InvalidLLMOutputError(
                "Ollama returned an invalid structured response."
            ) from exc

        return validated.model_dump(exclude_unset=True)
