from decimal import Decimal

from pydantic import BaseModel


class Recommendation(BaseModel):
    """Result returned by the bouquet recommendation engine."""

    composition: dict[str, dict[int, int]]
    total_price: Decimal