"""Reusable FastAPI dependencies."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.florist import Florist


def get_florist(
    florist_id: int,
    db: Session = Depends(get_db),
) -> Florist:
    """Return a florist or raise a 404 error."""

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

    return florist