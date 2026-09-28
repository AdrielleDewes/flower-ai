"""Wrapping API schemas."""

from decimal import Decimal

from pydantic import BaseModel


class WrappingResponse(BaseModel):
    """Wrapping information exposed by the API."""

    id: int
    name: str
    description: str | None
    price: Decimal
    available_quantity: int
    active: bool
