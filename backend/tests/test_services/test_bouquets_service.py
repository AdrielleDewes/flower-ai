from datetime import datetime, timedelta, timezone
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
from app.schemas.bouquet import BouquetCreate, BouquetSize, BouquetUpdate
from app.services.bouquets import (
    create_bouquet,
    delete_bouquet,
    get_bouquet_detail,
    get_florist_bouquets,
    update_bouquet,
    validate_bouquet_items,
)


def test_get_florist_bouquets_filters_florist_and_sorts_newest_first(
    db_session,
):
    florist = Florist(name="Test Florist")
    other_florist = Florist(name="Other Florist")
    db_session.add_all([florist, other_florist])
    db_session.flush()

    now = datetime.now(tz=timezone.utc)
    older_bouquet = Bouquet(
        florist_id=florist.id,
        name="Older Bouquet",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )
    newer_bouquet = Bouquet(
        florist_id=florist.id,
        name="Newer Bouquet",
        size=BouquetSize.MEDIUM.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    other_bouquet = Bouquet(
        florist_id=other_florist.id,
        name="Other Florist Bouquet",
        size=BouquetSize.LARGE.value,
        source="MANUAL",
        created_at=now + timedelta(days=1),
        updated_at=now + timedelta(days=1),
    )
    db_session.add_all([older_bouquet, newer_bouquet, other_bouquet])
    db_session.flush()

    result = get_florist_bouquets(db_session, florist.id)

    assert result == [newer_bouquet, older_bouquet]


def test_get_bouquet_detail_returns_bouquet_with_named_composition(db_session):
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    foliage = Foliage(name="Eucalyptus")
    wrapping = Wrapping(name="Kraft Paper")
    db_session.add_all([florist, flower, foliage, wrapping])
    db_session.flush()

    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Birthday Bouquet",
        description="For a celebration",
        size=BouquetSize.MEDIUM.value,
        source="GENERATED",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()
    db_session.add_all(
        [
            BouquetFlower(
                bouquet_id=bouquet.id,
                flower_id=flower.id,
                quantity=4,
            ),
            BouquetFoliage(
                bouquet_id=bouquet.id,
                foliage_id=foliage.id,
                quantity=2,
            ),
            BouquetWrapping(
                bouquet_id=bouquet.id,
                wrapping_id=wrapping.id,
                quantity=1,
            ),
        ]
    )
    db_session.flush()

    result = get_bouquet_detail(db_session, florist.id, bouquet.id)

    assert result == {
        "id": bouquet.id,
        "florist_id": florist.id,
        "name": "Birthday Bouquet",
        "description": "For a celebration",
        "size": BouquetSize.MEDIUM.value,
        "source": "GENERATED",
        "created_at": bouquet.created_at,
        "updated_at": bouquet.updated_at,
        "flowers": [{"id": flower.id, "name": "Rose", "quantity": 4}],
        "foliage": [{"id": foliage.id, "name": "Eucalyptus", "quantity": 2}],
        "wrapping": [{"id": wrapping.id, "name": "Kraft Paper", "quantity": 1}],
    }


def test_get_bouquet_detail_does_not_expose_another_florists_bouquet(
    db_session,
):
    florist = Florist(name="Bouquet Owner")
    other_florist = Florist(name="Other Florist")
    db_session.add_all([florist, other_florist])
    db_session.flush()

    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Private Bouquet",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()

    assert get_bouquet_detail(db_session, other_florist.id, bouquet.id) is None


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


def test_update_bouquet_replaces_details_and_composition(db_session):
    florist = Florist(name="Test Florist")
    old_flower = Flower(name="Old Rose")
    new_flower = Flower(name="New Rose")
    db_session.add_all([florist, old_flower, new_flower])
    db_session.flush()

    db_session.add_all(
        [
            FloristFlower(
                florist_id=florist.id,
                flower_id=old_flower.id,
                price=Decimal("10.00"),
                active=True,
            ),
            FloristFlower(
                florist_id=florist.id,
                flower_id=new_flower.id,
                price=Decimal("12.00"),
                active=True,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=old_flower.id,
                quantity=10,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=new_flower.id,
                quantity=10,
            ),
        ]
    )
    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Old bouquet",
        description="Old description",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()
    db_session.add(
        BouquetFlower(
            bouquet_id=bouquet.id,
            flower_id=old_flower.id,
            quantity=2,
        )
    )
    db_session.commit()
    previous_updated_at = bouquet.updated_at

    updated = update_bouquet(
        db_session,
        florist.id,
        bouquet.id,
        BouquetUpdate(
            name="Updated bouquet",
            description="New description",
            size=BouquetSize.MEDIUM,
            flowers={new_flower.id: 3},
        ),
    )

    assert updated is bouquet
    assert updated.name == "Updated bouquet"
    assert updated.description == "New description"
    assert updated.size == BouquetSize.MEDIUM.value
    assert updated.source == "MANUAL"
    assert updated.updated_at > previous_updated_at
    assert db_session.get(BouquetFlower, (bouquet.id, old_flower.id)) is None
    assert db_session.get(BouquetFlower, (bouquet.id, new_flower.id)).quantity == 3


def test_update_bouquet_preserves_fields_and_composition_not_supplied(db_session):
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    db_session.add_all([florist, flower])
    db_session.flush()
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Original name",
        description="Keep this description",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(bouquet)
    db_session.flush()
    db_session.add(
        BouquetFlower(
            bouquet_id=bouquet.id,
            flower_id=flower.id,
            quantity=2,
        )
    )
    db_session.commit()

    updated = update_bouquet(
        db_session,
        florist.id,
        bouquet.id,
        BouquetUpdate(name="New name"),
    )

    assert updated.name == "New name"
    assert updated.description == "Keep this description"
    assert updated.size == BouquetSize.SMALL.value
    assert updated.source == "MANUAL"
    assert db_session.get(BouquetFlower, (bouquet.id, flower.id)).quantity == 2


def test_update_bouquet_can_clear_description(db_session):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()
    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Bouquet",
        description="Existing description",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.commit()

    updated = update_bouquet(
        db_session,
        florist.id,
        bouquet.id,
        BouquetUpdate(description=None),
    )

    assert updated.description is None


def test_update_bouquet_validates_merged_composition_before_replacing_items(
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
                quantity=5,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=foliage.id,
                quantity=5,
            ),
            WrappingInventory(
                florist_id=florist.id,
                wrapping_id=wrapping.id,
                quantity=5,
            ),
        ]
    )
    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Original bouquet",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()
    db_session.add_all(
        [
            BouquetFlower(
                bouquet_id=bouquet.id,
                flower_id=flower.id,
                quantity=2,
            ),
            BouquetFoliage(
                bouquet_id=bouquet.id,
                foliage_id=foliage.id,
                quantity=1,
            ),
            BouquetWrapping(
                bouquet_id=bouquet.id,
                wrapping_id=wrapping.id,
                quantity=1,
            ),
        ]
    )
    db_session.commit()

    with pytest.raises(ValueError, match="not offered by the florist"):
        update_bouquet(
            db_session,
            florist.id,
            bouquet.id,
            BouquetUpdate(flowers={999: 2}),
        )

    assert db_session.get(BouquetFlower, (bouquet.id, flower.id)).quantity == 2
    assert db_session.get(BouquetFoliage, (bouquet.id, foliage.id)).quantity == 1
    assert db_session.get(BouquetWrapping, (bouquet.id, wrapping.id)).quantity == 1

    update_bouquet(
        db_session,
        florist.id,
        bouquet.id,
        BouquetUpdate(flowers={flower.id: 3}),
    )

    assert db_session.get(BouquetFlower, (bouquet.id, flower.id)).quantity == 3
    assert db_session.get(BouquetFoliage, (bouquet.id, foliage.id)).quantity == 1
    assert db_session.get(BouquetWrapping, (bouquet.id, wrapping.id)).quantity == 1


def test_update_bouquet_returns_none_for_another_florists_bouquet(db_session):
    florist = Florist(name="Bouquet Owner")
    other_florist = Florist(name="Other Florist")
    db_session.add_all([florist, other_florist])
    db_session.flush()
    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Private bouquet",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()

    result = update_bouquet(
        db_session,
        other_florist.id,
        bouquet.id,
        BouquetUpdate(
            name="Changed",
            size=BouquetSize.SMALL,
        ),
    )

    assert result is None


def test_delete_bouquet_deletes_bouquet_and_cascades_to_composition(db_session):
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    db_session.add_all([florist, flower])
    db_session.flush()
    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Bouquet to delete",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()
    db_session.add(
        BouquetFlower(
            bouquet_id=bouquet.id,
            flower_id=flower.id,
            quantity=2,
        )
    )
    db_session.commit()

    assert delete_bouquet(db_session, florist.id, bouquet.id) is True
    assert db_session.get(Bouquet, bouquet.id) is None
    assert db_session.get(BouquetFlower, (bouquet.id, flower.id)) is None


def test_delete_bouquet_returns_false_for_another_florists_bouquet(db_session):
    florist = Florist(name="Bouquet Owner")
    other_florist = Florist(name="Other Florist")
    db_session.add_all([florist, other_florist])
    db_session.flush()
    now = datetime.now(tz=timezone.utc)
    bouquet = Bouquet(
        florist_id=florist.id,
        name="Private bouquet",
        size=BouquetSize.SMALL.value,
        source="MANUAL",
        created_at=now,
        updated_at=now,
    )
    db_session.add(bouquet)
    db_session.flush()

    assert delete_bouquet(db_session, other_florist.id, bouquet.id) is False


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
        validate_bouquet_items(
            db_session,
            florist.id,
            bouquet_data.flowers,
            bouquet_data.foliage,
            bouquet_data.wrapping,
        )


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
        validate_bouquet_items(
            db_session,
            florist.id,
            bouquet_data.flowers,
            bouquet_data.foliage,
            bouquet_data.wrapping,
        )


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
        validate_bouquet_items(
            db_session,
            florist.id,
            bouquet_data.flowers,
            bouquet_data.foliage,
            bouquet_data.wrapping,
        )


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
        validate_bouquet_items(
            db_session,
            florist.id,
            bouquet_data.flowers,
            bouquet_data.foliage,
            bouquet_data.wrapping,
        )
