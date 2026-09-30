"""Provider independent contract for structured LLM output."""

from typing import Any, Protocol

from pydantic import BaseModel


class LLMProviderError(Exception):
    """The LLM provider could not produce a response."""


class InvalidLLMOutputError(ValueError):
    """The provider response does not match the requested output schema."""


class LLMProvider(Protocol):
    """Generate structured data using a supplied prompt and output schema."""

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
    ) -> dict[str, Any]:
        """Return data for schema validation or raise LLMProviderError."""
        ...
