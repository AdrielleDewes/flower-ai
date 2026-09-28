"""Recommendation logic for generating valid bouquet compositions.

This module contains the business rules used to find flowers,
build bouquet compositions, validate stock, and calculate prices.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Color,
    FloristFlower,
    FloristFoliage,
    FloristWrapping,
    Flower,
    FlowerColor,
    FlowerInventory,
    FlowerOccasion,
    FlowerStyle,
    Foliage,
    FoliageInventory,
    Occasion,
    Style,
    Wrapping,
    WrappingInventory,
)
from app.schemas.bouquet import BouquetRequest
from app.schemas.recommendation import Recommendation

SIZE_RANGES = {
    "SMALL": (3, 7),
    "MEDIUM": (8, 14),
    "LARGE": (15, 20),
}


def get_flower_quantity_range(size: str) -> tuple[int, int]:
    """Return the minimum and maximum stem counts for a bouquet size."""
    return SIZE_RANGES[size]


def get_foliage_quantity(
    size: str,
) -> int:
    """Return the foliage stem count assigned to a bouquet size."""
    foliage_quantities = {
        "SMALL": 1,
        "MEDIUM": 2,
        "LARGE": 3,
    }

    return foliage_quantities[size]


def select_primary_flower(
    candidate_flowers: list[Flower],
) -> Flower | None:
    """Choose the first candidate flower as the bouquet's primary flower."""
    if not candidate_flowers:
        return None

    return candidate_flowers[0]


def prioritize_preferred_flowers(
    candidate_flowers: list[Flower],
    preferred_flowers: list[str],
) -> list[Flower]:
    """Move requested flower names to the front in preference order."""

    if not preferred_flowers:
        return sorted(candidate_flowers, key=lambda flower: flower.name)

    flowers_by_name = {
        flower.name: flower
        for flower in candidate_flowers
    }

    preferred = [
        flowers_by_name[name]
        for name in preferred_flowers
        if name in flowers_by_name
    ]

    preferred_ids = {flower.id for flower in preferred}

    others = [
        flower
        for flower in candidate_flowers
        if flower.id not in preferred_ids
    ]

    others.sort(key=lambda flower: flower.name)

    return preferred + others


def get_primary_flower_quantity(
    size: str,
) -> int:
    """Return the number of primary flower stems for a bouquet size."""
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
    """Return the minimum bouquet stem count not supplied by its primary flower."""
    min_quantity, _ = get_flower_quantity_range(size)

    return max(min_quantity - primary_quantity, 0)


def build_bouquet_composition(
    candidate_flowers: list[Flower],
    size: str,
) -> dict[int, int]:
    """Build a composition using the first candidate to meet the minimum size."""
    min_quantity, _ = get_flower_quantity_range(size)

    if not candidate_flowers:
        return {}

    flower = candidate_flowers[0]

    return {
        flower.id: min_quantity,
    }


def build_cheapest_composition(
    db: Session,
    florist_id: int,
    candidate_flowers: list[Flower],
    size: str,
) -> dict[int, int]:
    """Fill the minimum bouquet size with the cheapest candidates in input order.

    Candidates are expected to be price-sorted. Return an empty composition
    when their available stock cannot meet the size's minimum stem count.
    """
    min_quantity, _ = get_flower_quantity_range(size)

    if not candidate_flowers:
        return {}

    composition = {}
    remaining_quantity = min_quantity

    for flower in candidate_flowers:
        if remaining_quantity <= 0:
            break

        available_stock = get_flower_stock(
            db,
            florist_id,
            flower.id,
        )

        quantity = min(
            available_stock,
            remaining_quantity,
        )

        if quantity > 0:
            composition[flower.id] = quantity
            remaining_quantity -= quantity

    if remaining_quantity > 0:
        return {}

    return composition


def build_preferred_flower_composition(
    db: Session,
    florist_id: int,
    candidate_flowers: list[Flower],
    primary_flower: Flower,
    size: str,
) -> dict[int, int]:
    """Build a stock-aware composition centered on the preferred primary flower.

    The primary receives its size-specific target, limited by available stock;
    secondary candidates fill the remaining minimum quantity. Return an empty
    composition when the minimum cannot be met.
    """
    min_quantity, _ = get_flower_quantity_range(size)

    if not candidate_flowers:
        return {}

    primary_stock = get_flower_stock(
        db,
        florist_id,
        primary_flower.id,
    )

    primary_quantity = min(
        get_primary_flower_quantity(size),
        primary_stock,
    )

    if primary_quantity <= 0:
        return {}

    composition = {
        primary_flower.id: primary_quantity,
    }

    remaining_quantity = min_quantity - primary_quantity

    if remaining_quantity <= 0:
        return composition

    composition = add_secondary_flowers(
        db,
        florist_id,
        candidate_flowers,
        primary_flower,
        composition,
        remaining_quantity,
    )

    if sum(composition.values()) < min_quantity:
        return {}

    return composition


def validate_composition(
    db: Session,
    florist_id: int,
    composition: dict,
    budget_max: Decimal | None,
) -> bool:
    """Check stock and budget constraints for a complete bouquet composition."""
    if not composition:
        return False

    if not has_sufficient_stock(
        db,
        florist_id,
        composition["flowers"],
    ):
        return False

    if not has_sufficient_foliage_stock(
        db,
        florist_id,
        composition["foliage"],
    ):
        return False

    if not has_sufficient_wrapping_stock(
        db,
        florist_id,
        composition["wrapping"],
    ):
        return False

    total = calculate_complete_bouquet_price(
        db,
        florist_id,
        composition,
    )

    return is_within_budget(
        total,
        budget_max,
    )


def add_secondary_flowers(
    db: Session,
    florist_id: int,
    candidate_flowers: list[Flower],
    primary_flower: Flower,
    composition: dict[int, int],
    remaining_quantity: int,
) -> dict[int, int]:
    """Distribute remaining quantities across secondary flowers."""
    if remaining_quantity <= 0:
        return composition

    secondary_flowers = [
        flower
        for flower in candidate_flowers
        if flower.id != primary_flower.id
    ]

    if not secondary_flowers:
        return composition

    stock = {
        flower.id: get_flower_stock(
            db,
            florist_id,
            flower.id,
        )
        for flower in secondary_flowers
    }

    while remaining_quantity > 0:
        added = False

        for flower in secondary_flowers:
            if remaining_quantity <= 0:
                break

            if stock[flower.id] <= 0:
                continue

            composition[flower.id] = (
                composition.get(flower.id, 0) + 1
            )
            stock[flower.id] -= 1
            remaining_quantity -= 1
            added = True

        if not added:
            break

    return composition


def get_flower_price(
    db: Session,
    florist_id: int,
    flower_id: int,
) -> Decimal:
    """Return the active florist price for a flower, or zero if unavailable."""
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
        return Decimal("0")  # noqa: FURB157

    return florist_flower.price


def calculate_bouquet_price(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> Decimal:
    """Calculate the total price of the flower portion of a bouquet."""
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


def calculate_foliage_price(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> Decimal:
    """Calculate the total price of the foliage portion of a bouquet."""
    total = Decimal(0)

    for foliage_id, quantity in composition.items():
        florist_foliage = (
            db.query(FloristFoliage)
            .filter(
                FloristFoliage.florist_id == florist_id,
                FloristFoliage.foliage_id == foliage_id,
                FloristFoliage.active.is_(True),
            )
            .first()
        )

        if florist_foliage is None:
            continue

        total += florist_foliage.price * quantity

    return total


def select_cheapest_foliage(
    candidate_foliage: list[Foliage],
    quantity: int,
    stock: dict[int, int],
) -> dict[int, int]:
    """Select foliage items while respecting stock and requested quantity."""
    if not candidate_foliage or quantity <= 0:
        return {}

    composition = {}
    remaining_quantity = quantity

    while remaining_quantity > 0:
        added = False

        for foliage in candidate_foliage:
            if remaining_quantity <= 0:
                break

            if stock.get(foliage.id, 0) <= 0:
                continue

            composition[foliage.id] = (
                composition.get(foliage.id, 0) + 1
            )
            stock[foliage.id] -= 1
            remaining_quantity -= 1
            added = True

        if not added:
            break

    return composition


def calculate_wrapping_price(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> Decimal:
    """Calculate the total price of the wrapping portion of a bouquet."""
    total = Decimal(0)

    for wrapping_id, quantity in composition.items():
        florist_wrapping = (
            db.query(FloristWrapping)
            .filter(
                FloristWrapping.florist_id == florist_id,
                FloristWrapping.wrapping_id == wrapping_id,
                FloristWrapping.active.is_(True),
            )
            .first()
        )

        if florist_wrapping is None:
            continue

        total += florist_wrapping.price * quantity

    return total


def calculate_complete_bouquet_price(
    db: Session,
    florist_id: int,
    composition: dict,
) -> Decimal:
    """Sum flower, foliage, and wrapping prices for a complete composition."""
    flower_price = calculate_bouquet_price(
        db,
        florist_id,
        composition["flowers"],
    )

    foliage_price = calculate_foliage_price(
        db,
        florist_id,
        composition["foliage"],
    )

    wrapping_price = calculate_wrapping_price(
        db,
        florist_id,
        composition["wrapping"],
    )

    return flower_price + foliage_price + wrapping_price


def sort_flowers_by_price(
    db: Session,
    florist_id: int,
    candidate_flowers: list[Flower],
) -> list[Flower]:
    """Return candidate flowers ordered from lowest to highest active price."""
    return sorted(
        candidate_flowers,
        key=lambda flower: (
            get_flower_price(
            db,
            florist_id,
            flower.id,
        ),
        ),
    )

def sort_foliage_by_price(
    db: Session,
    florist_id: int,
    candidate_foliage: list[Foliage],
) -> list[Foliage]:
    """Return candidate foliage ordered from lowest to highest florist price."""
    return sorted(
        candidate_foliage,
        key=lambda foliage: (
            db.query(FloristFoliage)
            .filter(
                FloristFoliage.florist_id == florist_id,
                FloristFoliage.foliage_id == foliage.id,
                FloristFoliage.active.is_(True),
            )
            .first()
            .price
        ),
    )


def sort_wrappings_by_price(
    db: Session,
    florist_id: int,
    candidate_wrappings: list[Wrapping],
) -> list[Wrapping]:
    """Return candidate wrappings ordered from lowest to highest florist price."""
    return sorted(
        candidate_wrappings,
        key=lambda wrapping: (
            db.query(FloristWrapping)
            .filter(
                FloristWrapping.florist_id == florist_id,
                FloristWrapping.wrapping_id == wrapping.id,
                FloristWrapping.active.is_(True),
            )
            .first()
            .price
        ),
    )


def select_cheapest_wrapping(
    candidate_wrappings: list[Wrapping],
) -> Wrapping | None:
    """Choose the first candidate wrapping, expected to be the cheapest."""
    if not candidate_wrappings:
        return None

    return candidate_wrappings[0]


def is_within_budget(
    total: Decimal,
    budget_max: Decimal | None,
) -> bool:
    """Return whether a total is within the optional maximum budget."""
    if budget_max is None:
        return True

    return total <= budget_max


def get_flower_stock(
    db: Session,
    florist_id: int,
    flower_id: int,
) -> int:
    """Return the available stock for a flower at a florist."""
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
    """Return the available stock for foliage at a florist."""
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


def get_wrapping_stock(
    db: Session,
    florist_id: int,
    wrapping_id: int,
) -> int:
    """Return the available stock for wrapping at a florist."""
    inventory = (
        db.query(WrappingInventory)
        .filter(
            WrappingInventory.florist_id == florist_id,
            WrappingInventory.wrapping_id == wrapping_id,
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
    """Check whether flower inventory covers every requested quantity."""
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
    """Check whether foliage inventory covers every requested quantity."""
    for foliage_id, required_quantity in composition.items():
        available_quantity = get_foliage_stock(
            db,
            florist_id,
            foliage_id,
        )

        if available_quantity < required_quantity:
            return False

    return True


def has_sufficient_wrapping_stock(
    db: Session,
    florist_id: int,
    composition: dict[int, int],
) -> bool:
    """Check whether wrapping inventory covers every requested quantity."""
    for wrapping_id, required_quantity in composition.items():
        available_quantity = get_wrapping_stock(
            db,
            florist_id,
            wrapping_id,
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
) -> dict[str, dict[int, int]]:
    """Build and validate a bouquet composition.

    Preference-based composition is attempted first. If it cannot satisfy
    stock or budget constraints, the cheapest valid composition is used as
    a fallback.
    """
    if not candidate_flowers:
        return {}

    candidate_flowers = prioritize_preferred_flowers(
        candidate_flowers,
        preferred_flowers,
    )

    primary_flower = select_primary_flower(candidate_flowers)

    if primary_flower is None:
        return {}

    flower_composition = build_preferred_flower_composition(
        db,
        florist_id,
        candidate_flowers,
        primary_flower,
        size,
    )

    if flower_composition:
        complete_composition = build_recommended_composition(
            db,
            florist_id,
            flower_composition,
            size,
        )

        if validate_composition(
            db,
            florist_id,
            complete_composition,
            budget_max,
        ):
            return complete_composition

    sorted_flowers = sort_flowers_by_price(
        db,
        florist_id,
        candidate_flowers,
    )

    cheapest_flower_composition = build_cheapest_composition(
        db,
        florist_id,
        sorted_flowers,
        size,
    )

    if not cheapest_flower_composition:
        return {}

    cheapest_complete_composition = build_recommended_composition(
        db,
        florist_id,
        cheapest_flower_composition,
        size,
    )

    if validate_composition(
        db,
        florist_id,
        cheapest_complete_composition,
        budget_max,
    ):
        return cheapest_complete_composition

    return {}


def find_candidate_flowers(
    db: Session,
    florist_id: int,
    request: BouquetRequest,
) -> list[Flower]:
    """Find flowers matching the request that are active and in stock."""
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
    """Find active foliage offered by the florist with available stock."""
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
    """Select the requested number of foliage items from the candidates."""
    if not candidate_foliage or quantity <= 0:
        return {}

    composition = {}

    for foliage in candidate_foliage:
        if quantity <= 0:
            break

        composition[foliage.id] = 1
        quantity -= 1

    return composition


def find_candidate_wrappings(
    db: Session,
    florist_id: int,
) -> list[Wrapping]:
    """Find active wrappings offered by the florist with available stock."""
    query = (
        db.query(Wrapping)
        .join(
            FloristWrapping,
            FloristWrapping.wrapping_id == Wrapping.id,
        )
        .join(
            WrappingInventory,
            (
                WrappingInventory.wrapping_id == Wrapping.id
            )
            & (
                WrappingInventory.florist_id == florist_id
            ),
        )
        .filter(
            FloristWrapping.florist_id == florist_id,
            FloristWrapping.active.is_(True),
            WrappingInventory.quantity > 0,
        )
    )

    return query.distinct().all()


def select_wrapping(
    candidate_wrappings: list[Wrapping],
) -> Wrapping | None:
    """Choose the first candidate wrapping."""
    if not candidate_wrappings:
        return None

    return candidate_wrappings[0]


def build_complete_composition(
    flower_composition: dict[int, int],
    foliage_composition: dict[int, int],
    wrapping: Wrapping | None,
) -> dict:
    """Combine flower, foliage, and optional wrapping selections."""
    return {
        "flowers": flower_composition,
        "foliage": foliage_composition,
        "wrapping": (
            {wrapping.id: 1}
            if wrapping is not None
            else {}
        ),
    }


def build_recommended_composition(
    db: Session,
    florist_id: int,
    flower_composition: dict[int, int],
    size: str,
) -> dict:
    """Complete a flower selection with the cheapest available foliage and wrapping."""
    candidate_foliage = find_candidate_foliage(
        db,
        florist_id,
    )

    sorted_foliage = sort_foliage_by_price(
        db,
        florist_id,
        candidate_foliage,
    )

    foliage_quantity = get_foliage_quantity(size)
    foliage_stock = {
        foliage.id: get_foliage_stock(
            db,
            florist_id,
            foliage.id,
        )
        for foliage in sorted_foliage
    }

    foliage_composition = select_cheapest_foliage(
        sorted_foliage,
        foliage_quantity,
        foliage_stock,
    )

    candidate_wrappings = find_candidate_wrappings(
        db,
        florist_id,
    )

    sorted_wrappings = sort_wrappings_by_price(
        db,
        florist_id,
        candidate_wrappings,
    )

    wrapping = select_cheapest_wrapping(
        sorted_wrappings,
    )

    return build_complete_composition(
        flower_composition,
        foliage_composition,
        wrapping,
    )


def generate_recommendation(
    db: Session,
    florist_id: int,
    request: BouquetRequest,
) -> Recommendation | None:
    """Generate a valid bouquet recommendation from a bouquet request."""
    candidate_flowers = find_candidate_flowers(
        db,
        florist_id,
        request,
    )

    composition = find_valid_composition(
        db,
        florist_id,
        candidate_flowers,
        request.size.value,
        request.budget_max,
        request.preferred_flowers,
    )

    if not composition:
        return None

    total_price = calculate_complete_bouquet_price(
        db,
        florist_id,
        composition,
    )

    return Recommendation(
        composition=composition,
        total_price=total_price,
    )
