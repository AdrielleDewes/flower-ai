"""Schemas for interpreting bouquet requests written in natural language."""

from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.bouquet import BouquetSize


class BouquetInterpretationInput(BaseModel):
    """Free text describing the bouquet the customer wants."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BouquetInterpretation(BaseModel):
    """Bouquet requirements identified in the text, with unknown values absent."""

    model_config = ConfigDict(extra="forbid")

    occasion: str | None = None
    styles: list[str] | None = None
    colors: list[str] | None = None
    size: BouquetSize | None = None
    budget_max: Decimal | None = None
    preferred_flowers: list[str] | None = None
    excluded_flowers: list[str] | None = None


BouquetRequestInterpretation = BouquetInterpretation


class BouquetRequestReadinessStatus(str, Enum):
    """Whether an interpretation contains all required request fields."""

    READY = "READY"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class BouquetRequestReadiness(BaseModel):
    """Completeness of an interpretation for a bouquet request."""

    status: BouquetRequestReadinessStatus
    missing_fields: list[str]
