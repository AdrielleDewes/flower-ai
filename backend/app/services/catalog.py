"""Florist catalog services."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Color, Flower, Occasion, Style
from app.models.florist import Florist, FloristFlower
from app.models.relationships import FlowerColor, FlowerOccasion, FlowerStyle
from app.schemas.catalog import InterpretationCatalog
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


def get_interpretation_catalog(db: Session, florist_id: int) -> InterpretationCatalog:
    """Read names associated with a florist's active flowers, regardless of stock."""
    if db.get(Florist, florist_id) is None:
        raise ValueError("Florist not found.")

    flower_ids = select(FloristFlower.flower_id).where(
        FloristFlower.florist_id == florist_id,
        FloristFlower.active.is_(True),
    )
    return InterpretationCatalog(
        flowers=list(db.scalars(
            select(Flower.name).where(Flower.id.in_(flower_ids)).order_by(Flower.name)
        )),
        occasions=list(db.scalars(
            select(Occasion.name).join(FlowerOccasion).where(
                FlowerOccasion.flower_id.in_(flower_ids)
            ).distinct().order_by(Occasion.name)
        )),
        styles=list(db.scalars(
            select(Style.name).join(FlowerStyle).where(
                FlowerStyle.flower_id.in_(flower_ids)
            ).distinct().order_by(Style.name)
        )),
        colors=list(db.scalars(
            select(Color.name).join(FlowerColor).where(
                FlowerColor.flower_id.in_(flower_ids)
            ).distinct().order_by(Color.name)
        )),
    )
