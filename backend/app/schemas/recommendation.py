from decimal import Decimal

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    """Item included in a bouquet recommendation."""

    id: int
    name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class Recommendation(BaseModel):
    """Result returned by the bouquet recommendation engine."""

    flowers: list[RecommendationItem]
    foliage: list[RecommendationItem]
    wrapping: list[RecommendationItem]
    total_price: Decimal
