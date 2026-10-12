"""Tests for provider backed bouquet request interpretation."""

from decimal import Decimal

import pytest

from app.schemas.bouquet import BouquetSize
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.services.llm_bouquet_request_interpreter import (
    InvalidLLMOutputError,
    LLMBouquetRequestInterpreter,
)
from app.services.llm_provider import LLMProviderError


class FakeLLMProvider:
    """Supply structured data or an error without calling a real model."""

    def __init__(self, output=None, error=None):
        """Set the result returned by generate_structured."""
        self.output = output
        self.error = error
        self.prompt = None
        self.schema = None

    def generate_structured(self, prompt, schema):
        """Record the request and return the configured result."""
        self.prompt = prompt
        self.schema = schema
        if self.error is not None:
            raise self.error
        return self.output


def test_interpreter_validates_structured_output():
    """The interpreter sends a prompt and validates every extracted field."""
    provider = FakeLLMProvider(
        output={
            "occasion": "Birthday",
            "styles": ["Romantic"],
            "colors": ["Red"],
            "size": "SMALL",
            "budget_max": "75.50",
            "preferred_flowers": ["Rose"],
            "excluded_flowers": ["Lily"],
        }
    )

    result = LLMBouquetRequestInterpreter(provider).interpret(
        "Red roses for a birthday, no lilies, up to 75.50"
    )

    assert isinstance(result, BouquetInterpretation)
    assert result.occasion == "Birthday"
    assert result.styles == ["Romantic"]
    assert result.colors == ["Red"]
    assert result.size is BouquetSize.SMALL
    assert result.budget_max == Decimal("75.50")
    assert result.preferred_flowers == ["Rose"]
    assert result.excluded_flowers == ["Lily"]
    assert provider.schema is BouquetInterpretation
    assert "BouquetInterpretation" in provider.prompt
    assert "Red roses for a birthday" in provider.prompt
    assert "excluded_flowers" in provider.prompt
    assert "Do not infer missing facts" in provider.prompt


def test_interpreter_preserves_unknown_fields_as_none():
    """Missing facts stay unknown when the provider omits them."""
    provider = FakeLLMProvider(output={"occasion": "Birthday"})

    result = LLMBouquetRequestInterpreter(provider).interpret("Birthday bouquet")

    assert result.occasion == "Birthday"
    assert result.styles is None
    assert result.colors is None
    assert result.size is None
    assert result.budget_max is None
    assert result.preferred_flowers is None
    assert result.excluded_flowers is None


@pytest.mark.parametrize("output", [{"size": "HUGE"}, {"other": "value"}])
def test_interpreter_rejects_invalid_provider_output(output):
    """Malformed structured output gets a distinct validation error."""
    provider = FakeLLMProvider(output=output)

    with pytest.raises(InvalidLLMOutputError) as error:
        LLMBouquetRequestInterpreter(provider).interpret("A bouquet")

    assert error.value.__cause__ is not None


def test_interpreter_propagates_provider_error():
    """A declared provider failure retains its original exception."""
    failure = LLMProviderError("Provider unavailable")
    provider = FakeLLMProvider(error=failure)

    with pytest.raises(LLMProviderError) as error:
        LLMBouquetRequestInterpreter(provider).interpret("A bouquet")

    assert error.value is failure


def test_interpreter_wraps_unexpected_provider_error():
    """Unexpected provider failures retain their cause for diagnosis."""
    failure = RuntimeError("Connection failed")
    provider = FakeLLMProvider(error=failure)

    with pytest.raises(LLMProviderError) as error:
        LLMBouquetRequestInterpreter(provider).interpret("A bouquet")

    assert error.value.__cause__ is failure
