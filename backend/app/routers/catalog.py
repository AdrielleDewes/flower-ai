"""Florist catalog API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.catalog import CatalogResponse
from app.services.catalog import get_florist_catalog

router = APIRouter(
    prefix="/florists/{florist_id}/catalog",
    tags=["catalog"],
)


@router.get("/", response_model=CatalogResponse)
def get_catalog(
    florist: Florist = Depends(get_florist),
    db: Session = Depends(get_db),
):
    """Return the complete catalog of a florist."""
    return get_florist_catalog(
        db,
        florist.id,
    )
