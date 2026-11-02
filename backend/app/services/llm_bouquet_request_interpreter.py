"""Bouquet request interpretation through an injected LLM provider."""

from pydantic import ValidationError

from app.prompts.bouquet_interpretation import build_bouquet_interpretation_prompt
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog
from app.services.catalog_output_schema import build_catalog_output_schema
from app.services.llm_provider import (
    InvalidLLMOutputError,
    LLMProvider,
    LLMProviderError,
)


class LLMBouquetRequestInterpreter:
    """Extract bouquet requirements using a provider's structured output."""

    def __init__(
        self, provider: LLMProvider, catalog: InterpretationCatalog,
        *, catalog_constraints: bool = False,
    ) -> None:
        """Use the given provider to interpret customer text."""
        self.provider = provider
        self.catalog = catalog.model_copy(deep=True)
        self._output_schema = (
            build_catalog_output_schema(self.catalog) if catalog_constraints else None
        )

    def interpret(self, text: str) -> BouquetInterpretation:
        """Return validated requirements extracted from the supplied text."""
        prompt = build_bouquet_interpretation_prompt(text, self.catalog)

        try:
            if self._output_schema is None:
                output = self.provider.generate_structured(
                    prompt=prompt, schema=BouquetInterpretation,
                )
            else:
                output = self.provider.generate_structured(
                    prompt=prompt, schema=BouquetInterpretation,
                    json_schema=self._output_schema,
                )
        except (LLMProviderError, InvalidLLMOutputError):
            raise
        except Exception as exc:
            raise LLMProviderError("LLM provider failed to generate a response.") from exc

        try:
            interpretation = BouquetInterpretation.model_validate(output)
        except ValidationError as exc:
            raise InvalidLLMOutputError(
                "LLM provider returned an invalid bouquet interpretation."
            ) from exc

        validate_catalog_values(interpretation, self.catalog)
        return interpretation


def validate_catalog_values(
    interpretation: BouquetInterpretation, catalog: InterpretationCatalog,
) -> None:
    """Reject noncanonical values using the same catalog supplied to the model."""
    allowed_values = {
        "occasion": catalog.occasions,
        "styles": catalog.styles,
        "colors": catalog.colors,
        "preferred_flowers": catalog.flowers,
        "excluded_flowers": catalog.flowers,
    }
    for field, allowed in allowed_values.items():
        value = getattr(interpretation, field)
        if value is None:
            continue
        values = [value] if isinstance(value, str) else value
        if any(item not in allowed for item in values):
            raise InvalidLLMOutputError(
                f"LLM returned a value outside the catalog for {field}."
            )
