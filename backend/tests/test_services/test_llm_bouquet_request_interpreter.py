"""Tests for provider backed bouquet request interpretation."""

from decimal import Decimal

import pytest

from app.schemas.bouquet import BouquetSize
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog
from app.services.llm_bouquet_request_interpreter import (
    InvalidLLMOutputError,
    LLMBouquetRequestInterpreter,
)
from app.services.llm_provider import LLMProviderError

CATALOG = InterpretationCatalog(
    occasions=["Birthday"], styles=["Romantic"], colors=["Red"],
    flowers=["Rose", "Lily"],
)

class FakeLLMProvider:
    """Supply structured data or an error without calling a real model."""

    def __init__(self, output=None, error=None):
        """Set the result returned by generate_structured."""
        self.output = output
        self.error = error
        self.prompt = None
        self.schema = None

    def generate_structured(self, prompt, schema, *, json_schema=None):
        """Record the request and return the configured result."""
        self.prompt = prompt
        self.schema = schema
        self.json_schema = json_schema
        if self.error is not None:
            raise self.error
        return self.output


def test_disabled_constraints_preserve_legacy_provider_call():
    """Baseline providers receive no new keyword when the experiment is off."""
    class LegacyProvider:
        def generate_structured(self, prompt, schema):
            return {}

    assert LLMBouquetRequestInterpreter(LegacyProvider(), CATALOG).interpret("Bouquet") == BouquetInterpretation()


def test_enabled_constraints_use_catalog_snapshot_and_preserve_absence():
    """Prompt, generation and validation use one snapshot across repeated calls."""
    catalog = CATALOG.model_copy(deep=True)
    provider = FakeLLMProvider(output={"colors": [], "size": None})
    interpreter = LLMBouquetRequestInterpreter(provider, catalog, catalog_constraints=True)
    catalog.colors.append("Purple")
    result = interpreter.interpret("A bouquet")
    output_schema = provider.json_schema
    assert provider.schema is BouquetInterpretation
    assert output_schema["properties"]["colors"]["anyOf"][0]["items"]["enum"] == ["Red"]
    assert "Purple" not in provider.prompt
    assert result == BouquetInterpretation()
    interpreter.interpret("Another bouquet")
    assert provider.json_schema is output_schema


@pytest.mark.parametrize("output", [
    {"colors": ["Purple"]}, {"styles": ["Red"]},
    {"preferred_flowers": ["Unknown"]}, {"size": "HUGE"},
])
def test_enabled_constraints_keep_post_generation_validation(output):
    """A provider ignoring constraints cannot bypass deterministic validation."""
    provider = FakeLLMProvider(output=output)
    with pytest.raises(InvalidLLMOutputError):
        LLMBouquetRequestInterpreter(provider, CATALOG, catalog_constraints=True).interpret("Bouquet")


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

    result = LLMBouquetRequestInterpreter(provider, CATALOG).interpret(
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

    result = LLMBouquetRequestInterpreter(provider, CATALOG).interpret("Birthday bouquet")

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
        LLMBouquetRequestInterpreter(provider, CATALOG).interpret("A bouquet")

    assert error.value.__cause__ is not None


def test_interpreter_propagates_provider_error():
    """A declared provider failure retains its original exception."""
    failure = LLMProviderError("Provider unavailable")
    provider = FakeLLMProvider(error=failure)

    with pytest.raises(LLMProviderError) as error:
        LLMBouquetRequestInterpreter(provider, CATALOG).interpret("A bouquet")

    assert error.value is failure


def test_interpreter_wraps_unexpected_provider_error():
    """Unexpected provider failures retain their cause for diagnosis."""
    failure = RuntimeError("Connection failed")
    provider = FakeLLMProvider(error=failure)

    with pytest.raises(LLMProviderError) as error:
        LLMBouquetRequestInterpreter(provider, CATALOG).interpret("A bouquet")

    assert error.value.__cause__ is failure


@pytest.mark.parametrize("output", [
    {"occasion": "Unknown"},
    {"styles": ["Romantic", "Red"]},
    {"colors": ["Red", "Rose"]},
    {"preferred_flowers": ["Rose", "Unknown"]},
    {"excluded_flowers": ["Unknown"]},
    {"preferred_flowers": ["rose"]},
])
def test_interpreter_rejects_values_outside_their_catalog_category(output):
    """Schema-valid hallucinations and noncanonical spellings are rejected."""
    provider = FakeLLMProvider(output=output)
    with pytest.raises(InvalidLLMOutputError, match=next(iter(output))):
        LLMBouquetRequestInterpreter(provider, CATALOG).interpret("A bouquet")


def test_prompt_uses_injected_catalog_without_filling_unknown_fields():
    """New catalog names reach the prompt and never become implicit defaults."""
    catalog = InterpretationCatalog(
        occasions=["Celebration"], styles=["Wild"], colors=["Amber"],
        flowers=["Calendula"],
    )
    provider = FakeLLMProvider(output={})
    result = LLMBouquetRequestInterpreter(provider, catalog).interpret("A bouquet")
    assert all(value is None for value in result.model_dump().values())
    assert catalog.model_dump_json() in provider.prompt
    assert "Birthday" not in provider.prompt
    assert "fields not mentioned by the customer must remain null" in provider.prompt
    assert "preferred_flowers and excluded_flowers" in provider.prompt


def test_empty_catalog_allows_only_unknown_values():
    """An empty catalog cannot silently fall back to ungrounded extraction."""
    catalog = InterpretationCatalog(occasions=[], styles=[], colors=[], flowers=[])
    provider = FakeLLMProvider(output={})
    interpreter = LLMBouquetRequestInterpreter(provider, catalog)
    assert interpreter.interpret("A bouquet").occasion is None
    provider.output = {"occasion": "Birthday"}
    with pytest.raises(InvalidLLMOutputError, match="occasion"):
        interpreter.interpret("Birthday bouquet")


def test_interpreter_accepts_new_canonical_names():
    """Grounding follows supplied catalog values rather than fixed vocabulary."""
    catalog = InterpretationCatalog(
        occasions=["Celebration"], styles=["Wild"], colors=["Amber"],
        flowers=["Calendula"],
    )
    output = {
        "occasion": "Celebration", "styles": ["Wild"], "colors": ["Amber"],
        "preferred_flowers": ["Calendula"], "excluded_flowers": None,
    }
    provider = FakeLLMProvider(output=output)
    result = LLMBouquetRequestInterpreter(provider, catalog).interpret("A bouquet")
    assert result.model_dump(exclude_unset=True) == output


def test_extractive_prompt_contract_and_normalization():
    """The prompt requires evidence; normalization never infers missing facts."""
    provider = FakeLLMProvider(output={
        "budget_max": "90", "styles": [], "colors": [],
        "preferred_flowers": [], "excluded_flowers": [],
    })
    result = LLMBouquetRequestInterpreter(provider, CATALOG).interpret("Up to 90")
    assert result.budget_max == Decimal(90)
    assert result.size is None
    assert result.occasion is None
    for field in ("styles", "colors", "preferred_flowers", "excluded_flowers"):
        assert getattr(result, field) is None
    for instruction in (
        "Every non-null field must have corresponding evidence in the customer text itself",
        "Do not recommend, complete the request, choose defaults",
        "Never infer size from budget",
        "Information present:",
        "Information absent:",
        "Never copy facts from these examples",
    ):
        assert instruction in provider.prompt


def test_interpreter_does_not_correct_model_size_from_customer_text():
    """Semantic extraction remains the model's responsibility, even when wrong."""
    provider = FakeLLMProvider(output={"size": "LARGE"})
    result = LLMBouquetRequestInterpreter(provider, CATALOG).interpret("A bouquet")
    assert result.size is BouquetSize.LARGE
