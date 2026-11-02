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
        *,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Use generation constraints and validate with the canonical model schema.

        Providers must honor json_schema for generation or fail explicitly, never
        silently retry without it. This contract does not add generic JSON Schema
        validation; callers must still validate application-specific constraints.
        """
        ...
