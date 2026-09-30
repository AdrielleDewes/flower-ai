"""Request schemas and options for bouquet recommendations."""

from datetime import datetime
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


class BouquetCreate(BaseModel):
    """Data required to save a bouquet."""

    name: str
    description: str | None = None
    size: BouquetSize
    source: str
    flowers: dict[int, int] = Field(default_factory=dict)
    foliage: dict[int, int] = Field(default_factory=dict)
    wrapping: dict[int, int] = Field(default_factory=dict)


class BouquetUpdate(BaseModel):
    """Data that can be updated on a saved bouquet."""

    name: str | None = None
    description: str | None = None
    size: BouquetSize | None = None
    flowers: dict[int, int] | None = None
    foliage: dict[int, int] | None = None
    wrapping: dict[int, int] | None = None


class BouquetResponse(BaseModel):
    """Saved bouquet information returned by the API."""

    id: int
    florist_id: int
    name: str
    description: str | None
    size: BouquetSize
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class BouquetItemResponse(BaseModel):
    """Catalog item included in a saved bouquet."""

    id: int
    name: str
    quantity: int


class BouquetDetailResponse(BouquetResponse):
    """Saved bouquet including its complete composition."""

    flowers: list[BouquetItemResponse]
    foliage: list[BouquetItemResponse]
    wrapping: list[BouquetItemResponse]
