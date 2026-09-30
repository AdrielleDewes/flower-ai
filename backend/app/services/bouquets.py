"""Bouquet persistence services."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.bouquet import (
    Bouquet,
    BouquetFlower,
    BouquetFoliage,
    BouquetWrapping,
)
from app.models.catalog import Flower, Foliage, Wrapping
from app.models.florist import FloristFlower, FloristFoliage, FloristWrapping
from app.models.inventory import (
    FlowerInventory,
    FoliageInventory,
    WrappingInventory,
)
from app.schemas.bouquet import BouquetCreate, BouquetUpdate


def get_florist_bouquets(
    db: Session,
    florist_id: int,
) -> list[Bouquet]:
    """Return saved bouquets for a florist."""
    return (
        db.query(Bouquet)
        .filter(Bouquet.florist_id == florist_id)
        .order_by(Bouquet.created_at.desc())
        .all()
    )


def get_bouquet_detail(
    db: Session,
    florist_id: int,
    bouquet_id: int,
) -> dict | None:
    """Return a saved bouquet with its complete composition."""
    bouquet = (
        db.query(Bouquet)
        .filter(
            Bouquet.id == bouquet_id,
            Bouquet.florist_id == florist_id,
        )
        .first()
    )

    if bouquet is None:
        return None

    flowers = (
        db.query(BouquetFlower, Flower)
        .join(
            Flower,
            Flower.id == BouquetFlower.flower_id,
        )
        .filter(BouquetFlower.bouquet_id == bouquet_id)
        .all()
    )
    foliage = (
        db.query(BouquetFoliage, Foliage)
        .join(
            Foliage,
            Foliage.id == BouquetFoliage.foliage_id,
        )
        .filter(BouquetFoliage.bouquet_id == bouquet_id)
        .all()
    )
    wrapping = (
        db.query(BouquetWrapping, Wrapping)
        .join(
            Wrapping,
            Wrapping.id == BouquetWrapping.wrapping_id,
        )
        .filter(BouquetWrapping.bouquet_id == bouquet_id)
        .all()
    )

    return {
        "id": bouquet.id,
        "florist_id": bouquet.florist_id,
        "name": bouquet.name,
        "description": bouquet.description,
        "size": bouquet.size,
        "source": bouquet.source,
        "created_at": bouquet.created_at,
        "updated_at": bouquet.updated_at,
        "flowers": [
            {
                "id": flower.id,
                "name": flower.name,
                "quantity": bouquet_flower.quantity,
            }
            for bouquet_flower, flower in flowers
        ],
        "foliage": [
            {
                "id": foliage_item.id,
                "name": foliage_item.name,
                "quantity": bouquet_foliage.quantity,
            }
            for bouquet_foliage, foliage_item in foliage
        ],
        "wrapping": [
            {
                "id": wrapping_item.id,
                "name": wrapping_item.name,
                "quantity": bouquet_wrapping.quantity,
            }
            for bouquet_wrapping, wrapping_item in wrapping
        ],
    }


def validate_bouquet_items(
    db: Session,
    florist_id: int,
    flowers: dict[int, int],
    foliage: dict[int, int],
    wrapping: dict[int, int],
) -> None:
    """Validate that all bouquet items belong to the florist."""
    flower_ids = set(flowers)
    foliage_ids = set(foliage)
    wrapping_ids = set(wrapping)

    quantities = [
        *flowers.values(),
        *foliage.values(),
        *wrapping.values(),
    ]

    if any(quantity <= 0 for quantity in quantities):
        raise ValueError("Bouquet item quantities must be greater than zero.")

    florist_flower_ids = {
        flower_id
        for (flower_id,) in (
            db.query(FloristFlower.flower_id)
            .filter(
                FloristFlower.florist_id == florist_id,
                FloristFlower.active.is_(True),
                FloristFlower.flower_id.in_(flower_ids),
            )
            .all()
        )
    }

    florist_foliage_ids = {
        foliage_id
        for (foliage_id,) in (
            db.query(FloristFoliage.foliage_id)
            .filter(
                FloristFoliage.florist_id == florist_id,
                FloristFoliage.active.is_(True),
                FloristFoliage.foliage_id.in_(foliage_ids),
            )
            .all()
        )
    }

    florist_wrapping_ids = {
        wrapping_id
        for (wrapping_id,) in (
            db.query(FloristWrapping.wrapping_id)
            .filter(
                FloristWrapping.florist_id == florist_id,
                FloristWrapping.active.is_(True),
                FloristWrapping.wrapping_id.in_(wrapping_ids),
            )
            .all()
        )
    }

    invalid_flowers = flower_ids - florist_flower_ids
    invalid_foliage = foliage_ids - florist_foliage_ids
    invalid_wrapping = wrapping_ids - florist_wrapping_ids

    if invalid_flowers or invalid_foliage or invalid_wrapping:
        raise ValueError("Bouquet contains items not offered by the florist.")

    for flower_id, quantity in flowers.items():
        stock = (
            db.query(FlowerInventory.quantity)
            .filter(
                FlowerInventory.florist_id == florist_id,
                FlowerInventory.flower_id == flower_id,
            )
            .scalar()
            or 0
        )

        if quantity > stock:
            raise ValueError(
                f"Not enough stock for flower {flower_id}."
            )

    for foliage_id, quantity in foliage.items():
        stock = (
            db.query(FoliageInventory.quantity)
            .filter(
                FoliageInventory.florist_id == florist_id,
                FoliageInventory.foliage_id == foliage_id,
            )
            .scalar()
            or 0
        )

        if quantity > stock:
            raise ValueError(
                f"Not enough stock for foliage {foliage_id}."
            )

    for wrapping_id, quantity in wrapping.items():
        stock = (
            db.query(WrappingInventory.quantity)
            .filter(
                WrappingInventory.florist_id == florist_id,
                WrappingInventory.wrapping_id == wrapping_id,
            )
            .scalar()
            or 0
        )

        if quantity > stock:
            raise ValueError(
                f"Not enough stock for wrapping {wrapping_id}."
            )


def create_bouquet(
    db: Session,
    florist_id: int,
    bouquet_data: BouquetCreate,
) -> Bouquet:
    """Create and persist a bouquet with its composition."""
    validate_bouquet_items(
        db,
        florist_id,
        bouquet_data.flowers,
        bouquet_data.foliage,
        bouquet_data.wrapping,
    )

    now = datetime.now(tz=timezone.utc)

    bouquet = Bouquet(
        florist_id=florist_id,
        name=bouquet_data.name,
        description=bouquet_data.description,
        size=bouquet_data.size.value,
        source=bouquet_data.source,
        created_at=now,
        updated_at=now,
    )

    db.add(bouquet)
    db.flush()

    for flower_id, quantity in bouquet_data.flowers.items():
        db.add(
            BouquetFlower(
                bouquet_id=bouquet.id,
                flower_id=flower_id,
                quantity=quantity,
            )
        )

    for foliage_id, quantity in bouquet_data.foliage.items():
        db.add(
            BouquetFoliage(
                bouquet_id=bouquet.id,
                foliage_id=foliage_id,
                quantity=quantity,
            )
        )

    for wrapping_id, quantity in bouquet_data.wrapping.items():
        db.add(
            BouquetWrapping(
                bouquet_id=bouquet.id,
                wrapping_id=wrapping_id,
                quantity=quantity,
            )
        )

    db.commit()
    db.refresh(bouquet)

    return bouquet


def update_bouquet(
    db: Session,
    florist_id: int,
    bouquet_id: int,
    bouquet_data: BouquetUpdate,
) -> Bouquet | None:
    """Update a saved bouquet and optionally replace its composition."""
    bouquet = (
        db.query(Bouquet)
        .filter(
            Bouquet.id == bouquet_id,
            Bouquet.florist_id == florist_id,
        )
        .first()
    )

    if bouquet is None:
        return None

    composition_changed = any(
        value is not None
        for value in (
            bouquet_data.flowers,
            bouquet_data.foliage,
            bouquet_data.wrapping,
        )
    )

    if composition_changed:
        flowers = (
            bouquet_data.flowers
            if bouquet_data.flowers is not None
            else {
                item.flower_id: item.quantity
                for item in db.query(BouquetFlower)
                .filter(BouquetFlower.bouquet_id == bouquet_id)
                .all()
            }
        )

        foliage = (
            bouquet_data.foliage
            if bouquet_data.foliage is not None
            else {
                item.foliage_id: item.quantity
                for item in db.query(BouquetFoliage)
                .filter(BouquetFoliage.bouquet_id == bouquet_id)
                .all()
            }
        )

        wrapping = (
            bouquet_data.wrapping
            if bouquet_data.wrapping is not None
            else {
                item.wrapping_id: item.quantity
                for item in db.query(BouquetWrapping)
                .filter(BouquetWrapping.bouquet_id == bouquet_id)
                .all()
            }
        )

        validate_bouquet_items(
            db,
            florist_id,
            flowers,
            foliage,
            wrapping,
        )

        if bouquet_data.flowers is not None:
            (
                db.query(BouquetFlower)
                .filter(BouquetFlower.bouquet_id == bouquet_id)
                .delete(synchronize_session=False)
            )

            for flower_id, quantity in flowers.items():
                db.add(
                    BouquetFlower(
                        bouquet_id=bouquet_id,
                        flower_id=flower_id,
                        quantity=quantity,
                    )
                )

        if bouquet_data.foliage is not None:
            (
                db.query(BouquetFoliage)
                .filter(BouquetFoliage.bouquet_id == bouquet_id)
                .delete(synchronize_session=False)
            )

            for foliage_id, quantity in foliage.items():
                db.add(
                    BouquetFoliage(
                        bouquet_id=bouquet_id,
                        foliage_id=foliage_id,
                        quantity=quantity,
                    )
                )

        if bouquet_data.wrapping is not None:
            (
                db.query(BouquetWrapping)
                .filter(BouquetWrapping.bouquet_id == bouquet_id)
                .delete(synchronize_session=False)
            )

            for wrapping_id, quantity in wrapping.items():
                db.add(
                    BouquetWrapping(
                        bouquet_id=bouquet_id,
                        wrapping_id=wrapping_id,
                        quantity=quantity,
                    )
                )

    if bouquet_data.name is not None:
        bouquet.name = bouquet_data.name
    if "description" in bouquet_data.model_fields_set:
        bouquet.description = bouquet_data.description
    if bouquet_data.size is not None:
        bouquet.size = bouquet_data.size.value
    bouquet.updated_at = datetime.now(tz=timezone.utc)

    db.commit()
    db.refresh(bouquet)

    return bouquet


def delete_bouquet(
    db: Session,
    florist_id: int,
    bouquet_id: int,
) -> bool:
    """Delete a saved bouquet belonging to a florist."""
    bouquet = (
        db.query(Bouquet)
        .filter(
            Bouquet.id == bouquet_id,
            Bouquet.florist_id == florist_id,
        )
        .first()
    )

    if bouquet is None:
        return False

    db.delete(bouquet)
    db.commit()

    return True
