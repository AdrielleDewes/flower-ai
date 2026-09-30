"""Catalog API schemas."""

from pydantic import BaseModel

from app.schemas.flower import FlowerResponse
from app.schemas.foliage import FoliageResponse
from app.schemas.wrapping import WrappingResponse


class CatalogResponse(BaseModel):
    """Complete catalog information for a florist."""

    flowers: list[FlowerResponse]
    foliage: list[FoliageResponse]
    wrappings: list[WrappingResponse]
