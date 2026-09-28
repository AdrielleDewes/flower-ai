"""Foliage catalog API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.foliage import FoliageResponse
from app.services.foliage import get_florist_foliage

router = APIRouter(
    prefix="/florists/{florist_id}/foliage",
    tags=["foliage"],
)


@router.get("/", response_model=list[FoliageResponse])
def list_foliage(
    florist: Florist = Depends(get_florist),
    db: Session = Depends(get_db),
):
    """List foliage offered by a florist."""
    return get_florist_foliage(
        db,
        florist.id,
    )
