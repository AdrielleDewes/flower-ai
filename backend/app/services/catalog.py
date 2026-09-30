"""Florist catalog services."""

from sqlalchemy.orm import Session

from app.services.flowers import get_florist_flowers
from app.services.foliage import get_florist_foliage
from app.services.wrappings import get_florist_wrappings


def get_florist_catalog(
    db: Session,
    florist_id: int,
) -> dict:
    """Return the complete catalog of a florist."""

    return {
        "flowers": get_florist_flowers(db, florist_id),
        "foliage": get_florist_foliage(db, florist_id),
        "wrappings": get_florist_wrappings(db, florist_id),
    }
