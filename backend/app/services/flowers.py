"""Flower catalog services."""

from sqlalchemy.orm import Session

from app.models.catalog import Flower
from app.models.florist import FloristFlower
from app.models.inventory import FlowerInventory


def get_florist_flowers(
    db: Session,
    florist_id: int,
) -> list[dict]:
    """Return active flowers offered by a florist with their price and stock."""

    results = (
        db.query(
            Flower,
            FloristFlower.price,
            FloristFlower.active,
            FlowerInventory.quantity,
        )
        .join(
            FloristFlower,
            FloristFlower.flower_id == Flower.id,
        )
        .join(
            FlowerInventory,
            (FlowerInventory.flower_id == Flower.id)
            & (FlowerInventory.florist_id == florist_id),
        )
        .filter(
            FloristFlower.florist_id == florist_id,
            FloristFlower.active.is_(True),
        )
        .order_by(Flower.name)
        .all()
    )

    return [
        {
            "id": flower.id,
            "name": flower.name,
            "description": flower.description,
            "price": price,
            "available_quantity": quantity,
            "active": active,
        }
        for flower, price, active, quantity in results
    ]