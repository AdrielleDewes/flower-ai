"""Public POC review contracts, independent of experimental annotation formats."""

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bouquet import BouquetRequest
from app.schemas.bouquet_interpretation import (
    BouquetInterpretation,
    BouquetInterpretationInput,
    BouquetRequestReadiness,
)
from app.schemas.catalog import InterpretationCatalog

InterpretationField = Literal[
    "occasion", "styles", "colors", "size", "budget_max", "preferred_flowers", "excluded_flowers",
]
InterpretationValue = str | Decimal | list[str] | None


class InterpretationRequest(BouquetInterpretationInput):
    """Accept text only; inference settings remain server-controlled."""

    model_config = ConfigDict(extra="forbid")


class SourceRelation(str, Enum):
    """Content relationships are distinct from unresolved client-review issues."""

    AGREEMENT = "AGREEMENT"
    COMPLEMENTARY = "COMPLEMENTARY"
    DIVERGENCE = "DIVERGENCE"
    CONTRADICTION = "CONTRADICTION"
    UNRESOLVED = "UNRESOLVED"
    NOT_IDENTIFIED = "NOT_IDENTIFIED"


class InterpretationEvidence(BaseModel):
    """Source-text support; offsets refer to the normalized text returned by the API."""

    model_config = ConfigDict(extra="forbid")
    start: int
    end: int
    text: str


class FieldSources(BaseModel):
    """Preserve source values; only resolved extractor values enter extractor_value."""

    model_config = ConfigDict(extra="forbid")
    relation: SourceRelation
    llm_value: InterpretationValue = None
    extractor_value: InterpretationValue = None
    evidence: list[InterpretationEvidence] = Field(default_factory=list)


class ReviewIssue(BaseModel):
    """A deterministic, actionable reason to complete or correct the draft."""

    model_config = ConfigDict(extra="forbid")
    field: InterpretationField
    related_fields: list[InterpretationField] = Field(default_factory=list)
    code: Literal[
        "EXTRACTOR_UNCERTAIN", "EXTRACTOR_CONFLICT", "SCALAR_CONTRADICTION",
        "BUDGET_DIVERGENCE", "LIST_DIVERGENCE", "LIST_ORDER_DIVERGENCE",
        "UNCONFIRMED_LLM_VALUES", "PREFERENCE_EXCLUSION_CONFLICT",
    ]
    message: str


class InterpretationMergeResult(BaseModel):
    """Canonical proposal, readiness and review state; never a recommendation."""

    model_config = ConfigDict(extra="forbid")
    interpretation: BouquetInterpretation
    readiness: BouquetRequestReadiness
    issues: list[ReviewIssue]
    field_sources: dict[InterpretationField, FieldSources]
    requires_review: bool
    recommendation_request: BouquetRequest | None = None


class InterpretationResponse(InterpretationMergeResult):
    """Stateless interpretation draft plus valid choices for a future review form."""

    text: str
    options: InterpretationCatalog
