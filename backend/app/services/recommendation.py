from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Color,
    FloristFlower,
    Flower,
    FlowerColor,
    FlowerInventory,
    FlowerOccasion,
    FlowerStyle,
    Occasion,
    Style,
)
from app.schemas.bouquet import BouquetRequest

SIZE_RANGES = {
    "SMALL": (3, 7),
    "MEDIUM": (8, 14),
    "LARGE": (15, 20),
}


def get_flower_quantity_range(size: str) -> tuple[int, int]:
    return SIZE_RANGES[size]


def select_primary_flower(
    candidate_flowers: list[Flower],
) -> Flower | None:
    if not candidate_flowers:
        return None

    return candidate_flowers[0]


def get_primary_flower_quantity(
    size: str,
) -> int:
    primary_quantities = {
        "SMALL": 2,
        "MEDIUM": 4,
        "LARGE": 7,
    }

    return primary_quantities[size]


def build_bouquet_composition(
    candidate_flowers: list[Flower],
    size: str,
) -> dict[int, int]:
    min_quantity, _ = get_flower_quantity_range(size)

    if not candidate_flowers:
        return {}

    flower = candidate_flowers[0]

    return {
        flower.id: min_quantity,
    }


def add_secondary_flowers(
    candidate_flowers: list[Flower],
    primary_flower: Flower,
    composition: dict[int, int],
    remaining_quantity: int,
) -> dict[int, int]:
    for flower in candidate_flowers:
        if remaining_quantity <= 0:
            break

        if flower.id == primary_flower.id:
            continue

        composition[flower.id] = 1
        remaining_quantity -= 1

    return composition


def calculate_bouquet_price(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> Decimal:
    total = Decimal(0)

    for flower_id, quantity in composition.items():
        florist_flower = (
            db.query(FloristFlower)
            .filter(
                FloristFlower.florist_id == florist_id,
                FloristFlower.flower_id == flower_id,
                FloristFlower.active.is_(True),
            )
            .first()
        )

        if florist_flower is None:
            continue

        total += florist_flower.price * quantity

    return total


def is_within_budget(
    total: Decimal,
    budget_max: Decimal | None,
) -> bool:
    if budget_max is None:
        return True

    return total <= budget_max


def get_flower_stock(
    db: Session,
    florist_id: int,
    flower_id: int,
) -> int:
    inventory = (
        db.query(FlowerInventory)
        .filter(
            FlowerInventory.florist_id == florist_id,
            FlowerInventory.flower_id == flower_id,
        )
        .first()
    )

    if inventory is None:
        return 0

    return inventory.quantity


def has_sufficient_stock(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> bool:
    for flower_id, required_quantity in composition.items():
        available_quantity = get_flower_stock(
            db,
            florist_id,
            flower_id,
        )

        if available_quantity < required_quantity:
            return False

    return True


def find_valid_composition(
    db: Session,
    florist_id: int,
    candidate_flowers: list[Flower],
    size: str,
    budget_max: Decimal | None,
) -> dict[int, int]:
    min_quantity, _ = get_flower_quantity_range(size)

    if not candidate_flowers:
        return {}

    primary_flower = select_primary_flower(candidate_flowers)

    if primary_flower is None:
        return {}

    primary_quantity = get_primary_flower_quantity(size)

    composition = {
        primary_flower.id: primary_quantity,
    }

    remaining_quantity = min_quantity - primary_quantity

    composition = add_secondary_flowers(
        candidate_flowers,
        primary_flower,
        composition,
        remaining_quantity,
    )

    total_quantity = sum(composition.values())

    if total_quantity < min_quantity:
        return {}

    if not has_sufficient_stock(
        db,
        florist_id,
        composition,
    ):
        return {}

    total = calculate_bouquet_price(
        db,
        florist_id,
        composition,
    )

    if not is_within_budget(total, budget_max):
        return {}

    return composition


def find_candidate_flowers(
    db: Session,
    florist_id: int,
    request: BouquetRequest,
) -> list[Flower]:
    occasion = (
        db.query(Occasion)
        .filter(Occasion.name == request.occasion)
        .first()
    )

    if occasion is None:
        return []

    style_ids = []

    if request.styles:
        style_ids = (
            db.query(Style.id)
            .filter(Style.name.in_(request.styles))
            .all()
        )

        style_ids = [style_id for (style_id,) in style_ids]

        if not style_ids:
            return []

    color_ids = (
        db.query(Color.id)
        .filter(Color.name.in_(request.colors))
        .all()
    )

    color_ids = [color_id for (color_id,) in color_ids]

    if not color_ids:
        return []

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
        .join(
            FlowerOccasion,
            FlowerOccasion.flower_id == Flower.id,
        )
        .join(
            FlowerStyle,
            FlowerStyle.flower_id == Flower.id,
        )
        .join(
            FlowerColor,
            FlowerColor.flower_id == Flower.id,
        )
        .filter(
            FloristFlower.florist_id == florist_id,
            FloristFlower.active.is_(True),
            FlowerInventory.quantity > 0,
            FlowerOccasion.occasion_id == occasion.id,
            FlowerColor.color_id.in_(color_ids),
            *(
                [FlowerStyle.style_id.in_(style_ids)]
                if style_ids
                else []
            ),
        )
    )

    return query.distinct().all()