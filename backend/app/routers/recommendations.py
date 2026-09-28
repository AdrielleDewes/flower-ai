"""Recommendation API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
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
    florist_id: int,
    request: BouquetRequest,
    db: Session = Depends(get_db),
):
    """Generate a bouquet recommendation."""
    florist = (
        db.query(Florist)
        .filter(Florist.id == florist_id)
        .first()
    )

    if florist is None:
        raise HTTPException(
            status_code=404,
            detail="Florist not found.",
        )

    recommendation = generate_recommendation(
        db,
        florist_id=florist_id,
        request=request,
    )

    if recommendation is None:
        raise HTTPException(
            status_code=422,
            detail="No valid bouquet recommendation could be generated.",
        )

    return recommendation
