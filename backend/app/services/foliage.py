"""Foliage catalog services."""

from sqlalchemy.orm import Session

from app.models.catalog import Foliage
from app.models.florist import FloristFoliage
from app.models.inventory import FoliageInventory


def get_florist_foliage(
    db: Session,
    florist_id: int,
) -> list[dict]:
    """Return active foliage offered by a florist with price and stock."""

    results = (
        db.query(
            Foliage,
            FloristFoliage.price,
            FloristFoliage.active,
            FoliageInventory.quantity,
        )
        .join(
            FloristFoliage,
            FloristFoliage.foliage_id == Foliage.id,
        )
        .join(
            FoliageInventory,
            (FoliageInventory.foliage_id == Foliage.id)
            & (FoliageInventory.florist_id == florist_id),
        )
        .filter(
            FloristFoliage.florist_id == florist_id,
            FloristFoliage.active.is_(True),
        )
        .order_by(Foliage.name)
        .all()
    )

    return [
        {
            "id": foliage.id,
            "name": foliage.name,
            "description": foliage.description,
            "price": price,
            "available_quantity": quantity,
            "active": active,
        }
        for foliage, price, active, quantity in results
    ]
