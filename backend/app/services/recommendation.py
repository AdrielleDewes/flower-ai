from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Color,
    FloristFlower,
    FloristFoliage,
    Flower,
    FlowerColor,
    FlowerInventory,
    FlowerOccasion,
    FlowerStyle,
    Foliage,
    FoliageInventory,
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


def get_foliage_quantity(
    size: str,
) -> int:
    foliage_quantities = {
        "SMALL": 1,
        "MEDIUM": 2,
        "LARGE": 3,
    }

    return foliage_quantities[size]


def select_primary_flower(
    candidate_flowers: list[Flower],
) -> Flower | None:
    if not candidate_flowers:
        return None

    return candidate_flowers[0]


def prioritize_preferred_flowers(
    candidate_flowers: list[Flower],
    preferred_flowers: list[str],
) -> list[Flower]:
    if not preferred_flowers:
        return candidate_flowers

    preferred = []
    others = []

    for flower in candidate_flowers:
        if flower.name in preferred_flowers:
            preferred.append(flower)
        else:
            others.append(flower)

    return preferred + others


def get_primary_flower_quantity(
    size: str,
) -> int:
    primary_quantities = {
        "SMALL": 2,
        "MEDIUM": 4,
        "LARGE": 7,
    }

    return primary_quantities[size]


def get_remaining_quantity(
    size: str,
    primary_quantity: int,
) -> int:
    min_quantity, _ = get_flower_quantity_range(size)

    return max(min_quantity - primary_quantity, 0)


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


def build_cheapest_composition(
    candidate_flowers: list[Flower],
    size: str,
) -> dict[int, int]:
    min_quantity, _ = get_flower_quantity_range(size)

    if not candidate_flowers:
        return {}

    composition = {}
    remaining_quantity = min_quantity
    index = 0

    while remaining_quantity > 0:
        flower = candidate_flowers[index]
        composition[flower.id] = composition.get(flower.id, 0) + 1
        remaining_quantity -= 1
        index = (index + 1) % len(candidate_flowers)

    return composition


def validate_composition(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
    budget_max: Decimal | None,
) -> bool:
    if not composition:
        return False

    if not has_sufficient_stock(
        db,
        florist_id,
        composition,
    ):
        return False

    total = calculate_bouquet_price(
        db,
        florist_id,
        composition,
    )

    return is_within_budget(total, budget_max)


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


def sort_flowers_by_price(
    db: Session,
    florist_id: int,
    candidate_flowers: list[Flower],
) -> list[Flower]:
    return sorted(
        candidate_flowers,
        key=lambda flower: (
            calculate_bouquet_price(
                db,
                florist_id,
                {flower.id: 1},
            )
        ),
    )


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


def get_foliage_stock(
    db: Session,
    florist_id: int,
    foliage_id: int,
) -> int:
    inventory = (
        db.query(FoliageInventory)
        .filter(
            FoliageInventory.florist_id == florist_id,
            FoliageInventory.foliage_id == foliage_id,
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


def has_sufficient_foliage_stock(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> bool:
    for foliage_id, required_quantity in composition.items():
        available_quantity = get_foliage_stock(
            db,
            florist_id,
            foliage_id,
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
    preferred_flowers: list[str],
) -> dict[int, int]:
    if not candidate_flowers:
        return {}

    candidate_flowers = prioritize_preferred_flowers(
        candidate_flowers,
        preferred_flowers,
    )

    primary_flower = select_primary_flower(candidate_flowers)

    if primary_flower is None:
        return {}

    primary_quantity = get_primary_flower_quantity(size)

    composition = {
        primary_flower.id: primary_quantity,
    }

    remaining_quantity = get_remaining_quantity(
        size,
        primary_quantity,
    )

    composition = add_secondary_flowers(
        candidate_flowers,
        primary_flower,
        composition,
        remaining_quantity,
    )

    if validate_composition(
        db,
        florist_id,
        composition,
        budget_max,
    ):
        return composition

    sorted_flowers = sort_flowers_by_price(
        db,
        florist_id,
        candidate_flowers,
    )

    cheapest_composition = build_cheapest_composition(
        sorted_flowers,
        size,
    )

    if validate_composition(
        db,
        florist_id,
        cheapest_composition,
        budget_max,
    ):
        return cheapest_composition

    return {}


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

        if request.styles and not style_ids:
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
            *(
                [~Flower.name.in_(request.excluded_flowers)]
                if request.excluded_flowers
                else []
            ),
        )
    )

    return query.distinct().all()


def find_candidate_foliage(
    db: Session,
    florist_id: int,
) -> list[Foliage]:
    query = (
        db.query(Foliage)
        .join(
            FloristFoliage,
            FloristFoliage.foliage_id == Foliage.id,
        )
        .join(
            FoliageInventory,
            (
                FoliageInventory.foliage_id == Foliage.id
            )
            & (
                FoliageInventory.florist_id == florist_id
            ),
        )
        .filter(
            FloristFoliage.florist_id == florist_id,
            FloristFoliage.active.is_(True),
            FoliageInventory.quantity > 0,
        )
    )

    return query.distinct().all()


def select_foliage(
    candidate_foliage: list[Foliage],
    quantity: int,
) -> dict[int, int]:
    if not candidate_foliage or quantity <= 0:
        return {}

    composition = {}

    for foliage in candidate_foliage:
        if quantity <= 0:
            break

        composition[foliage.id] = 1
        quantity -= 1

    return composition