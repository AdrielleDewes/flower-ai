from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.bouquet import BouquetRequest, BouquetSize


def make_request(**overrides) -> BouquetRequest:
    data = {
        "occasion": "Birthday",
        "styles": ["Romantic"],
        "colors": ["Pink"],
        "size": "MEDIUM",
    }
    data.update(overrides)
    return BouquetRequest(**data)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SMALL", BouquetSize.SMALL),
        ("MEDIUM", BouquetSize.MEDIUM),
        ("LARGE", BouquetSize.LARGE),
    ],
)
def test_bouquet_size_accepts_supported_values(value, expected):
    assert make_request(size=value).size is expected


def test_bouquet_size_rejects_invalid_value():
    with pytest.raises(ValidationError):
        make_request(size="EXTRA_LARGE")


@pytest.mark.parametrize("field", ["occasion", "styles", "colors", "size"])
def test_bouquet_request_requires_core_fields(field):
    data = {
        "occasion": "Birthday",
        "styles": ["Romantic"],
        "colors": ["Pink"],
        "size": "MEDIUM",
    }
    del data[field]

    with pytest.raises(ValidationError):
        BouquetRequest(**data)


def test_budget_fields_parse_decimal_values_and_default_to_none():
    request = make_request(budget_min="20.50", budget_max="75.00")

    assert request.budget_min == Decimal("20.50")
    assert request.budget_max == Decimal("75.00")
    assert make_request().budget_min is None
    assert make_request().budget_max is None


def test_default_lists_are_independent_between_requests():
    first = make_request(styles=[], colors=[])
    second = make_request(styles=[], colors=[])

    first.preferred_flowers.append("Rose")
    first.excluded_flowers.append("Lily")

    assert second.preferred_flowers == []
    assert second.excluded_flowers == []


def test_preferred_and_excluded_flowers_are_preserved():
    request = make_request(
        preferred_flowers=["Rose", "Tulip"],
        excluded_flowers=["Lily"],
    )

    assert request.preferred_flowers == ["Rose", "Tulip"]
    assert request.excluded_flowers == ["Lily"]


def test_preferred_and_excluded_flowers_default_to_empty_lists():
    request = make_request()

    assert request.preferred_flowers == []
    assert request.excluded_flowers == []