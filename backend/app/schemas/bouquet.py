"""Request schemas and options for bouquet recommendations."""

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class BouquetSize(str, Enum):
    """Supported bouquet size options."""

    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class BouquetRequest(BaseModel):
    """Customer requirements used to generate a bouquet recommendation."""

    occasion: str
    styles: list[str]
    colors: list[str]
    size: BouquetSize
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    preferred_flowers: list[str] = Field(default_factory=list)
    excluded_flowers: list[str] = Field(default_factory=list)
