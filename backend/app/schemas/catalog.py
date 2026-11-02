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


class InterpretationCatalog(BaseModel):
    """Canonical names available for interpretation, without price or stock."""

    occasions: list[str]
    styles: list[str]
    colors: list[str]
    flowers: list[str]
