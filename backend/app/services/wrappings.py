"""Wrapping catalog services."""

from sqlalchemy.orm import Session

from app.models.catalog import Wrapping
from app.models.florist import FloristWrapping
from app.models.inventory import WrappingInventory


def get_florist_wrappings(
    db: Session,
    florist_id: int,
) -> list[dict]:
    """Return active wrappings offered by a florist with price and stock."""

    results = (
        db.query(
            Wrapping,
            FloristWrapping.price,
            FloristWrapping.active,
            WrappingInventory.quantity,
        )
        .join(
            FloristWrapping,
            FloristWrapping.wrapping_id == Wrapping.id,
        )
        .join(
            WrappingInventory,
            (WrappingInventory.wrapping_id == Wrapping.id)
            & (WrappingInventory.florist_id == florist_id),
        )
        .filter(
            FloristWrapping.florist_id == florist_id,
            FloristWrapping.active.is_(True),
        )
        .order_by(Wrapping.name)
        .all()
    )

    return [
        {
            "id": wrapping.id,
            "name": wrapping.name,
            "description": wrapping.description,
            "price": price,
            "available_quantity": quantity,
            "active": active,
        }
        for wrapping, price, active, quantity in results
    ]
