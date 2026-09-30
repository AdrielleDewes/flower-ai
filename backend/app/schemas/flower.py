"""Flower API schemas."""

from decimal import Decimal

from pydantic import BaseModel


class FlowerResponse(BaseModel):
    """Flower information exposed by the API."""

    id: int
    name: str
    description: str | None
    price: Decimal
    available_quantity: int
    active: bool