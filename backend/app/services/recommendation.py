from sqlalchemy.orm import Session

from app.models import Flower, FlowerInventory, FloristFlower
from app.schemas.bouquet import BouquetRequest


def find_candidate_flowers(
    db: Session,
    florist_id: int,
    request: BouquetRequest,
) -> list[Flower]:
    query = (
        db.query(Flower)
        .join(
            FloristFlower,
            FloristFlower.flower_id == Flower.id,
        )
        .join(
            FlowerInventory,
            (
                FlowerInventory.flower_id == Flower.id
            )
            & (
                FlowerInventory.florist_id == florist_id
            ),
        )
        .filter(
            FloristFlower.florist_id == florist_id,
            FloristFlower.active.is_(True),
            FlowerInventory.quantity > 0,
        )
    )

    return query.all()