"""Wrapping catalog API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.wrapping import WrappingResponse
from app.services.wrappings import get_florist_wrappings

router = APIRouter(
    prefix="/florists/{florist_id}/wrappings",
    tags=["wrappings"],
)


@router.get("/", response_model=list[WrappingResponse])
def list_wrappings(
    florist: Florist = Depends(get_florist),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """List wrappings offered by a florist."""
    return get_florist_wrappings(
        db,
        florist.id,
    )
