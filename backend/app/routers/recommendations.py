"""Recommendation API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.bouquet import BouquetRequest
from app.schemas.recommendation import Recommendation
from app.services.recommendation import generate_recommendation

router = APIRouter(tags=["recommendations"])


@router.post(
    "/florists/{florist_id}/recommendations",
    response_model=Recommendation,
)
def create_recommendation(
    request: BouquetRequest,
    florist: Florist = Depends(get_florist),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Generate a bouquet recommendation."""
    recommendation = generate_recommendation(
        db,
        florist_id=florist.id,
        request=request,
    )

    if recommendation is None:
        raise HTTPException(
            status_code=422,
            detail="No valid bouquet recommendation could be generated.",
        )

    return recommendation
