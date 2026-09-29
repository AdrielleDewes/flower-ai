"""Bouquet API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.bouquet import BouquetCreate
from app.services.bouquets import create_bouquet

router = APIRouter(
    prefix="/florists/{florist_id}/bouquets",
    tags=["bouquets"],
)


@router.post(
    "/",
    responses={
        400: {
            "description": "Invalid bouquet composition",
        },
    },
)
def create_bouquet_endpoint(
    bouquet_data: BouquetCreate,
    florist: Florist = Depends(get_florist),
    db: Session = Depends(get_db),
):
    """Create a bouquet for a florist."""
    try:
        return create_bouquet(
            db,
            florist.id,
            bouquet_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
