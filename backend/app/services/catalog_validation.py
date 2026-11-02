"""Shared validation for machine proposals and user-entered preferences."""

from decimal import Decimal

from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog


class CatalogValidationError(ValueError):
    """A preference does not belong to its florist catalog category."""

    def __init__(self, field: str) -> None:
        """Retain the field without exposing infrastructure or arbitrary values."""
        self.field = field
        super().__init__(f"Value outside the catalog for {field}.")


def validate_catalog_values(
    interpretation: BouquetInterpretation, catalog: InterpretationCatalog,
) -> None:
    """Require exact canonical spelling within the correct category."""
    allowed_values = {
        "occasion": catalog.occasions, "styles": catalog.styles,
        "colors": catalog.colors, "preferred_flowers": catalog.flowers,
        "excluded_flowers": catalog.flowers,
    }
    for field, allowed in allowed_values.items():
        value = getattr(interpretation, field)
        if value is None:
            continue
        values = [value] if isinstance(value, str) else value
        if any(item not in allowed for item in values):
            raise CatalogValidationError(field)


def validate_budget_max(value: Decimal | None) -> None:
    """Reject unusable upper budgets before they reach deterministic pricing."""
    if value is not None and (not value.is_finite() or value <= 0):
        raise ValueError("budget_max must be finite and greater than zero.")
