"""Deterministic completion of interpreted bouquet requirements."""

from app.schemas.bouquet import BouquetRequest
from app.schemas.bouquet_interpretation import (
    BouquetRequestInterpretation,
    BouquetRequestReadiness,
    BouquetRequestReadinessStatus,
)


def assess_bouquet_interpretation(
    interpretation: BouquetRequestInterpretation,
) -> BouquetRequestReadiness:
    """Identify fields required by BouquetRequest that remain unknown."""
    missing_fields = [
        name
        for name, field in BouquetRequest.model_fields.items()
        if field.is_required() and getattr(interpretation, name, None) is None
    ]

    status = (
        BouquetRequestReadinessStatus.NEEDS_CLARIFICATION
        if missing_fields
        else BouquetRequestReadinessStatus.READY
    )

    return BouquetRequestReadiness(
        status=status,
        missing_fields=missing_fields,
    )


def to_bouquet_request(
    interpretation: BouquetRequestInterpretation,
) -> BouquetRequest:
    """Convert a complete interpretation using BouquetRequest validation."""
    readiness = assess_bouquet_interpretation(interpretation)
    if readiness.status is not BouquetRequestReadinessStatus.READY:
        raise ValueError(
            "Missing required bouquet request fields: "
            + ", ".join(readiness.missing_fields)
        )

    return BouquetRequest.model_validate(
        interpretation.model_dump(exclude_none=True)
    )
