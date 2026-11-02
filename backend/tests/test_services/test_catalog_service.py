import pytest

from app.models.catalog import Color, Flower, Occasion, Style
from app.models.florist import Florist, FloristFlower
from app.models.inventory import FlowerInventory
from app.models.relationships import FlowerColor, FlowerOccasion, FlowerStyle
from app.services import catalog


def test_get_florist_catalog_combines_catalog_services(db_session, monkeypatch):
    florist_id = 42
    calls = []
    flowers = [{"id": 1, "name": "Rose"}]
    foliage = [{"id": 2, "name": "Eucalyptus"}]
    wrappings = [{"id": 3, "name": "Kraft Paper"}]

    def fake_get_florist_flowers(db, requested_florist_id):
        calls.append(("flowers", db, requested_florist_id))
        return flowers

    def fake_get_florist_foliage(db, requested_florist_id):
        calls.append(("foliage", db, requested_florist_id))
        return foliage

    def fake_get_florist_wrappings(db, requested_florist_id):
        calls.append(("wrappings", db, requested_florist_id))
        return wrappings

    monkeypatch.setattr(catalog, "get_florist_flowers", fake_get_florist_flowers)
    monkeypatch.setattr(catalog, "get_florist_foliage", fake_get_florist_foliage)
    monkeypatch.setattr(
        catalog,
        "get_florist_wrappings",
        fake_get_florist_wrappings,
    )

    result = catalog.get_florist_catalog(db_session, florist_id)

    assert result == {
        "flowers": flowers,
        "foliage": foliage,
        "wrappings": wrappings,
    }
    assert calls == [
        ("flowers", db_session, florist_id),
        ("foliage", db_session, florist_id),
        ("wrappings", db_session, florist_id),
    ]


def test_interpretation_catalog_is_scoped_active_and_independent_of_stock(db_session):
    """Use canonical active offerings and attributes without inventory filtering."""
    db_session.add_all([
        Florist(id=1, name="First"), Florist(id=2, name="Second"),
        Flower(id=1, name="Rose"), Flower(id=2, name="Lily"),
        Flower(id=3, name="Tulip"), Flower(id=4, name="Daisy"),
        Color(id=1, name="Red"), Color(id=2, name="White"),
        Style(id=1, name="Romantic"), Style(id=2, name="Wild"),
        Occasion(id=1, name="Birthday"), Occasion(id=2, name="Wedding"),
    ])
    db_session.flush()
    db_session.add_all([
        FloristFlower(florist_id=1, flower_id=1, active=True, price=10),
        FloristFlower(florist_id=1, flower_id=2, active=False, price=20),
        FloristFlower(florist_id=2, flower_id=3, active=True, price=30),
        FloristFlower(florist_id=1, flower_id=4, active=True, price=5),
        FlowerInventory(florist_id=1, flower_id=1, quantity=0),
        FlowerColor(flower_id=1, color_id=1),
        FlowerColor(flower_id=4, color_id=1),
        FlowerColor(flower_id=2, color_id=2),
        FlowerStyle(flower_id=1, style_id=1),
        FlowerStyle(flower_id=3, style_id=2),
        FlowerOccasion(flower_id=1, occasion_id=1),
        FlowerOccasion(flower_id=3, occasion_id=2),
    ])
    db_session.flush()

    result = catalog.get_interpretation_catalog(db_session, 1)
    assert result.model_dump() == {
        "occasions": ["Birthday"], "styles": ["Romantic"], "colors": ["Red"],
        "flowers": ["Daisy", "Rose"],
    }
    other = catalog.get_interpretation_catalog(db_session, 2)
    assert other.flowers == ["Tulip"]
    assert other.styles == ["Wild"]
    assert other.occasions == ["Wedding"]

    db_session.get(FloristFlower, (1, 1)).active = False
    db_session.flush()
    refreshed = catalog.get_interpretation_catalog(db_session, 1)
    assert refreshed.flowers == ["Daisy"]
    assert refreshed.styles == []
    assert refreshed.occasions == []


def test_interpretation_catalog_empty_and_missing_florist(db_session):
    """Empty catalogs remain empty and nonexistent florists are rejected."""
    db_session.add(Florist(id=1, name="Empty"))
    db_session.flush()
    result = catalog.get_interpretation_catalog(db_session, 1)
    assert all(values == [] for values in result.model_dump().values())
    with pytest.raises(ValueError, match="Florist not found"):
        catalog.get_interpretation_catalog(db_session, 2)
