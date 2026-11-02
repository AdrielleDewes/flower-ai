"""Contract tests for natural language bouquet interpretation schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.bouquet import BouquetSize
from app.schemas.bouquet_interpretation import (
    BouquetInterpretationInput,
    BouquetRequestInterpretation,
)


def test_interpretation_input_accepts_nonempty_text():
    """Keep customer text available to an interpreter."""
    request = BouquetInterpretationInput(text="  Roses for a birthday  ")

    assert request.text == "Roses for a birthday"


@pytest.mark.parametrize("text", ["", "   "])
def test_interpretation_input_rejects_blank_text(text):
    """A request must contain text that can be interpreted."""
    with pytest.raises(ValidationError):
        BouquetInterpretationInput(text=text)


def test_interpretation_leaves_unmentioned_fields_unknown():
    """Missing facts remain unknown rather than receiving defaults."""
    interpretation = BouquetRequestInterpretation()

    assert all(
        value is None
        for value in interpretation.model_dump().values()
    )


def test_interpretation_accepts_bouquet_request_fields():
    """Parsed values use the types expected by BouquetRequest."""
    interpretation = BouquetRequestInterpretation(
        occasion="Birthday",
        styles=["Romantic"],
        colors=["Red"],
        size="SMALL",
        budget_max="75.50",
        preferred_flowers=["Rose"],
        excluded_flowers=[],
    )

    assert interpretation.occasion == "Birthday"
    assert interpretation.styles == ["Romantic"]
    assert interpretation.colors == ["Red"]
    assert interpretation.size is BouquetSize.SMALL
    assert interpretation.budget_max == Decimal("75.50")
    assert interpretation.preferred_flowers == ["Rose"]
    assert interpretation.excluded_flowers is None


@pytest.mark.parametrize("field, value", [("size", "EXTRA_LARGE"), ("budget_max", "unknown")])
def test_interpretation_rejects_invalid_typed_values(field, value):
    """Structured fields reject values outside their declared types."""
    with pytest.raises(ValidationError):
        BouquetRequestInterpretation(**{field: value})


@pytest.mark.parametrize("field", ["styles", "colors", "preferred_flowers", "excluded_flowers"])
@pytest.mark.parametrize("value", [None, []])
def test_optional_lists_normalize_absence_to_none(field, value):
    """Null and empty lists share the same absence representation in JSON."""
    interpretation = BouquetRequestInterpretation(**{field: value})
    assert getattr(interpretation, field) is None
    assert interpretation.model_dump(mode="json")[field] is None
    assert BouquetRequestInterpretation.model_validate_json(
        interpretation.model_dump_json()
    ) == interpretation


@pytest.mark.parametrize("field", ["styles", "colors", "preferred_flowers", "excluded_flowers"])
def test_list_normalization_preserves_identified_values(field):
    """Normalization does not erase or rewrite extracted names."""
    interpretation = BouquetRequestInterpretation(**{field: ["Canonical name"]})
    assert getattr(interpretation, field) == ["Canonical name"]


@pytest.mark.parametrize("field", ["styles", "colors", "preferred_flowers", "excluded_flowers"])
def test_list_normalization_does_not_hide_invalid_types(field):
    """Malformed output must fail validation instead of becoming absent."""
    with pytest.raises(ValidationError):
        BouquetRequestInterpretation(**{field: ""})
