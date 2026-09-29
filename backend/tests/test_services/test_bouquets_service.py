from decimal import Decimal

import pytest

from app.models import (
    Bouquet,
    BouquetFlower,
    BouquetFoliage,
    BouquetWrapping,
    Florist,
    FloristFlower,
    FloristFoliage,
    FloristWrapping,
    Flower,
    FlowerInventory,
    Foliage,
    FoliageInventory,
    Wrapping,
    WrappingInventory,
)
from app.schemas.bouquet import BouquetCreate, BouquetSize
from app.services.bouquets import create_bouquet, validate_bouquet_items


def test_create_bouquet_persists_bouquet_and_all_composition_items(db_session):
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    foliage = Foliage(name="Eucalyptus")
    wrapping = Wrapping(name="Kraft Paper")
    db_session.add_all([florist, flower, foliage, wrapping])
    db_session.flush()
    db_session.add_all(
        [
            FloristFlower(
                florist_id=florist.id,
                flower_id=flower.id,
                price=Decimal("12.00"),
                active=True,
            ),
            FloristFoliage(
                florist_id=florist.id,
                foliage_id=foliage.id,
                price=Decimal("5.00"),
                active=True,
            ),
            FloristWrapping(
                florist_id=florist.id,
                wrapping_id=wrapping.id,
                price=Decimal("4.00"),
                active=True,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=flower.id,
                quantity=10,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=foliage.id,
                quantity=10,
            ),
            WrappingInventory(
                florist_id=florist.id,
                wrapping_id=wrapping.id,
                quantity=10,
            ),
        ]
    )
    db_session.flush()

    bouquet = create_bouquet(
        db_session,
        florist.id,
        BouquetCreate(
            name="Birthday Bouquet",
            description="A colorful bouquet",
            size=BouquetSize.MEDIUM,
            source="RECOMMENDATION",
            flowers={flower.id: 3},
            foliage={foliage.id: 2},
            wrapping={wrapping.id: 1},
        ),
    )

    assert bouquet.id is not None
    assert bouquet.florist_id == florist.id
    assert bouquet.name == "Birthday Bouquet"
    assert bouquet.description == "A colorful bouquet"
    assert bouquet.size == BouquetSize.MEDIUM.value
    assert bouquet.source == "RECOMMENDATION"
    assert bouquet.created_at == bouquet.updated_at

    assert db_session.get(Bouquet, bouquet.id) is bouquet
    assert db_session.get(BouquetFlower, (bouquet.id, flower.id)).quantity == 3
    assert db_session.get(BouquetFoliage, (bouquet.id, foliage.id)).quantity == 2
    assert db_session.get(BouquetWrapping, (bouquet.id, wrapping.id)).quantity == 1


def test_create_bouquet_persists_empty_composition(db_session):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()

    bouquet = create_bouquet(
        db_session,
        florist.id,
        BouquetCreate(
            name="Empty Composition",
            size=BouquetSize.SMALL,
            source="MANUAL",
        ),
    )

    assert bouquet.id is not None
    assert (
        db_session.query(BouquetFlower)
        .filter_by(bouquet_id=bouquet.id)
        .all()
        == []
    )
    assert (
        db_session.query(BouquetFoliage)
        .filter_by(bouquet_id=bouquet.id)
        .all()
        == []
    )
    assert (
        db_session.query(BouquetWrapping)
        .filter_by(bouquet_id=bouquet.id)
        .all()
        == []
    )


def test_validate_bouquet_items_rejects_items_not_offered_by_florist(
    db_session,
):
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    foliage = Foliage(name="Eucalyptus")
    wrapping = Wrapping(name="Kraft Paper")
    db_session.add_all([florist, flower, foliage, wrapping])
    db_session.flush()
    db_session.add_all(
        [
            FlowerInventory(
                florist_id=florist.id,
                flower_id=flower.id,
                quantity=2,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=foliage.id,
                quantity=1,
            ),
            WrappingInventory(
                florist_id=florist.id,
                wrapping_id=wrapping.id,
                quantity=1,
            ),
        ]
    )
    db_session.flush()

    bouquet_data = BouquetCreate(
        name="Unavailable Bouquet",
        size=BouquetSize.SMALL,
        source="MANUAL",
        flowers={flower.id: 2},
        foliage={foliage.id: 1},
        wrapping={wrapping.id: 1},
    )

    with pytest.raises(
        ValueError,
        match="Bouquet contains items not offered by the florist.",
    ):
        validate_bouquet_items(db_session, florist.id, bouquet_data)


def test_validate_bouquet_items_checks_offering_before_stock(db_session):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()
    bouquet_data = BouquetCreate(
        name="Unknown Flower Bouquet",
        size=BouquetSize.SMALL,
        source="MANUAL",
        flowers={999: 1},
    )

    with pytest.raises(
        ValueError,
        match="Bouquet contains items not offered by the florist.",
    ):
        validate_bouquet_items(db_session, florist.id, bouquet_data)


@pytest.mark.parametrize("quantity", [0, -1])
def test_validate_bouquet_items_rejects_nonpositive_quantities(
    db_session,
    quantity,
):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()
    bouquet_data = BouquetCreate(
        name="Invalid Quantity Bouquet",
        size=BouquetSize.SMALL,
        source="MANUAL",
        flowers={1: quantity},
    )

    with pytest.raises(
        ValueError,
        match="Bouquet item quantities must be greater than zero.",
    ):
        validate_bouquet_items(db_session, florist.id, bouquet_data)


@pytest.mark.parametrize(
    ("item_type", "expected_message"),
    [
        ("flower", "Not enough stock for flower"),
        ("foliage", "Not enough stock for foliage"),
        ("wrapping", "Not enough stock for wrapping"),
    ],
)
def test_validate_bouquet_items_rejects_missing_stock(
    db_session,
    item_type,
    expected_message,
):
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    foliage = Foliage(name="Eucalyptus")
    wrapping = Wrapping(name="Kraft Paper")
    db_session.add_all([florist, flower, foliage, wrapping])
    db_session.flush()
    db_session.add_all(
        [
            FloristFlower(
                florist_id=florist.id,
                flower_id=flower.id,
                price=Decimal("12.00"),
                active=True,
            ),
            FloristFoliage(
                florist_id=florist.id,
                foliage_id=foliage.id,
                price=Decimal("5.00"),
                active=True,
            ),
            FloristWrapping(
                florist_id=florist.id,
                wrapping_id=wrapping.id,
                price=Decimal("4.00"),
                active=True,
            ),
        ]
    )
    db_session.flush()

    item_ids = {
        "flowers": {flower.id: 1} if item_type == "flower" else {},
        "foliage": {foliage.id: 1} if item_type == "foliage" else {},
        "wrapping": {wrapping.id: 1} if item_type == "wrapping" else {},
    }
    bouquet_data = BouquetCreate(
        name="Out of Stock Bouquet",
        size=BouquetSize.SMALL,
        source="MANUAL",
        **item_ids,
    )

    with pytest.raises(ValueError, match=expected_message):
        validate_bouquet_items(db_session, florist.id, bouquet_data)
