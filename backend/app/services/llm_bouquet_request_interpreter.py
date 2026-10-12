"""Bouquet request interpretation through an injected LLM provider."""

from pydantic import ValidationError

from app.prompts.bouquet_interpretation import build_bouquet_interpretation_prompt
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.services.llm_provider import (
    InvalidLLMOutputError,
    LLMProvider,
    LLMProviderError,
)


class LLMBouquetRequestInterpreter:
    """Extract bouquet requirements using a provider's structured output."""

    def __init__(self, provider: LLMProvider) -> None:
        """Use the given provider to interpret customer text."""
        self.provider = provider

    def interpret(self, text: str) -> BouquetInterpretation:
        """Return validated requirements extracted from the supplied text."""
        prompt = build_bouquet_interpretation_prompt(text)

        try:
            output = self.provider.generate_structured(
                prompt=prompt,
                schema=BouquetInterpretation,
            )
        except (LLMProviderError, InvalidLLMOutputError):
            raise
        except Exception as exc:
            raise LLMProviderError("LLM provider failed to generate a response.") from exc

        try:
            return BouquetInterpretation.model_validate(output)
        except ValidationError as exc:
            raise InvalidLLMOutputError(
                "LLM provider returned an invalid bouquet interpretation."
            ) from exc
