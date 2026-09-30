"""Foliage API schemas."""

from decimal import Decimal

from pydantic import BaseModel


class FoliageResponse(BaseModel):
    """Foliage information exposed by the API."""

    id: int
    name: str
    description: str | None
    price: Decimal
    available_quantity: int
    active: bool
