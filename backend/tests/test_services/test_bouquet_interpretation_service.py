"""Tests for deterministic bouquet interpretation readiness and conversion."""

from decimal import Decimal

import pytest

from app.schemas.bouquet import BouquetRequest, BouquetSize
from app.schemas.bouquet_interpretation import (
    BouquetRequestInterpretation,
    BouquetRequestReadinessStatus,
)
from app.services.bouquet_interpretation import (
    assess_bouquet_interpretation,
    to_bouquet_request,
)


def test_complete_interpretation_is_ready_without_optional_fields():
    """The required fields in BouquetRequest determine readiness."""
    interpretation = BouquetRequestInterpretation(
        occasion="Birthday",
        styles=[],
        colors=["Red"],
        size=BouquetSize.SMALL,
    )

    readiness = assess_bouquet_interpretation(interpretation)

    assert readiness.status is BouquetRequestReadinessStatus.READY
    assert readiness.missing_fields == []


def test_incomplete_interpretation_lists_missing_required_fields():
    """Unknown required values need clarification, including absent lists."""
    interpretation = BouquetRequestInterpretation(
        occasion="Birthday",
        budget_max=Decimal("80.00"),
    )

    readiness = assess_bouquet_interpretation(interpretation)

    assert readiness.status is BouquetRequestReadinessStatus.NEEDS_CLARIFICATION
    assert readiness.missing_fields == ["styles", "colors", "size"]
    with pytest.raises(ValueError, match="styles, colors, size"):
        to_bouquet_request(interpretation)


def test_complete_interpretation_converts_to_valid_bouquet_request():
    """Conversion retains extracted values and uses BouquetRequest defaults."""
    interpretation = BouquetRequestInterpretation(
        occasion="Birthday",
        styles=["Romantic"],
        colors=["Red"],
        size=BouquetSize.MEDIUM,
        budget_max=Decimal("80.00"),
        preferred_flowers=["Rose"],
        excluded_flowers=[],
    )

    request = to_bouquet_request(interpretation)

    assert isinstance(request, BouquetRequest)
    assert request.occasion == "Birthday"
    assert request.styles == ["Romantic"]
    assert request.colors == ["Red"]
    assert request.size is BouquetSize.MEDIUM
    assert request.budget_max == Decimal("80.00")
    assert request.budget_min is None
    assert request.preferred_flowers == ["Rose"]
    assert request.excluded_flowers == []
