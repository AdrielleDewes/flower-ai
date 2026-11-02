"""Validate explicit user choices independently of natural-language interpretation."""

from sqlalchemy.orm import Session

from app.schemas.bouquet import BouquetRequest
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.services.catalog import get_interpretation_catalog
from app.services.catalog_validation import validate_budget_max, validate_catalog_values


def validate_recommendation_request(db: Session, florist_id: int, request: BouquetRequest) -> None:
    """Recheck current catalog and hard constraints before entering the existing engine."""
    catalog = get_interpretation_catalog(db, florist_id)
    interpretation = BouquetInterpretation.model_validate(request.model_dump(exclude={"budget_min"}))
    validate_catalog_values(interpretation, catalog)
    validate_budget_max(request.budget_max)
    if set(request.preferred_flowers) & set(request.excluded_flowers):
        raise ValueError("A flower cannot be both preferred and excluded.")
