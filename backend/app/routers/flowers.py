"""Flower catalog API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.flower import FlowerResponse
from app.services.flowers import get_florist_flowers

router = APIRouter(
    prefix="/florists/{florist_id}/flowers",
    tags=["flowers"],
)


@router.get("/", response_model=list[FlowerResponse])
def list_flowers(
    florist: Florist = Depends(get_florist),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """List flowers offered by a florist."""
    return get_florist_flowers(
        db,
        florist.id,
    )
