"""Bouquet API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist
from app.models.florist import Florist
from app.schemas.bouquet import (
    BouquetCreate,
    BouquetDetailResponse,
    BouquetResponse,
)
from app.services.bouquets import (
    create_bouquet,
    get_bouquet_detail,
    get_florist_bouquets,
)

router = APIRouter(
    prefix="/florists/{florist_id}/bouquets",
    tags=["bouquets"],
)


@router.get(
    "/",
    response_model=list[BouquetResponse],
)
def list_bouquets(
    florist: Florist = Depends(get_florist),
    db: Session = Depends(get_db),
):
    """List saved bouquets for a florist."""
    return get_florist_bouquets(
        db,
        florist.id,
    )


@router.get(
    "/{bouquet_id}",
    response_model=BouquetDetailResponse,
)
def get_bouquet(
    bouquet_id: int,
    florist: Florist = Depends(get_florist),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a saved bouquet and its composition."""
    bouquet = get_bouquet_detail(
        db,
        florist.id,
        bouquet_id,
    )

    if bouquet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bouquet not found.",
        )

    return bouquet


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
