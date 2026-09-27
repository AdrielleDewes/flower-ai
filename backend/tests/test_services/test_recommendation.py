from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models import (
    Color,
    Florist,
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
from app.services.recommendation import (
    add_secondary_flowers,
    build_cheapest_composition,
    calculate_bouquet_price,
    find_candidate_flowers,
    find_candidate_foliage,
    find_valid_composition,
    get_flower_quantity_range,
    get_flower_stock,
    get_foliage_quantity,
    get_foliage_stock,
    get_primary_flower_quantity,
    get_remaining_quantity,
    has_sufficient_foliage_stock,
    has_sufficient_stock,
    is_within_budget,
    prioritize_preferred_flowers,
    select_foliage,
    select_primary_flower,
    sort_flowers_by_price,
    validate_composition,
)


@pytest.fixture
def catalog(db_session):
    florist = Florist(name="Test Florist")
    rose = Flower(name="Rose")
    tulip = Flower(name="Tulip")
    daisy = Flower(name="Daisy")
    lily = Flower(name="Lily")
    flowers = [rose, tulip, daisy, lily]

    eucalyptus = Foliage(name="Eucalyptus")
    fern = Foliage(name="Fern")
    ruscus = Foliage(name="Ruscus")
    olive_branch = Foliage(name="Olive Branch")
    foliage = [eucalyptus, fern, ruscus, olive_branch]

    pink = Color(name="Pink", hex_code="#FFC0CB")
    white = Color(name="White", hex_code="#FFFFFF")
    yellow = Color(name="Yellow", hex_code="#FFFF00")
    colors = {"Pink": pink, "White": white, "Yellow": yellow}

    romantic = Style(name="Romantic")
    delicate = Style(name="Delicate")
    birthday = Occasion(name="Birthday")
    anniversary = Occasion(name="Anniversary")

    db_session.add_all(
        [
            florist,
            *flowers,
            *foliage,
            *colors.values(),
            romantic,
            delicate,
            birthday,
            anniversary,
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            FlowerColor(flower_id=rose.id, color_id=pink.id),
            FlowerColor(flower_id=rose.id, color_id=white.id),
            FlowerColor(flower_id=tulip.id, color_id=pink.id),
            FlowerColor(flower_id=tulip.id, color_id=yellow.id),
            FlowerColor(flower_id=daisy.id, color_id=white.id),
            FlowerColor(flower_id=daisy.id, color_id=yellow.id),
            FlowerColor(flower_id=lily.id, color_id=white.id),
            FlowerStyle(flower_id=rose.id, style_id=romantic.id),
            FlowerStyle(flower_id=tulip.id, style_id=delicate.id),
            FlowerStyle(flower_id=daisy.id, style_id=romantic.id),
            FlowerStyle(flower_id=lily.id, style_id=delicate.id),
            FlowerOccasion(flower_id=rose.id, occasion_id=birthday.id),
            FlowerOccasion(flower_id=tulip.id, occasion_id=birthday.id),
            FlowerOccasion(flower_id=daisy.id, occasion_id=birthday.id),
            FlowerOccasion(flower_id=lily.id, occasion_id=birthday.id),
            FlowerOccasion(flower_id=rose.id, occasion_id=anniversary.id),
        ]
    )

    db_session.add_all(
        [
            FloristFlower(
                florist_id=florist.id,
                flower_id=rose.id,
                price=Decimal("12.00"),
                active=True,
            ),
            FloristFlower(
                florist_id=florist.id,
                flower_id=tulip.id,
                price=Decimal("8.00"),
                active=True,
            ),
            FloristFlower(
                florist_id=florist.id,
                flower_id=daisy.id,
                price=Decimal("6.00"),
                active=True,
            ),
            FloristFlower(
                florist_id=florist.id,
                flower_id=lily.id,
                price=Decimal("4.00"),
                active=False,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=rose.id,
                quantity=30,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=tulip.id,
                quantity=25,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=daisy.id,
                quantity=35,
            ),
            FlowerInventory(
                florist_id=florist.id,
                flower_id=lily.id,
                quantity=20,
            ),
            FloristFoliage(
                florist_id=florist.id,
                foliage_id=eucalyptus.id,
                price=Decimal("5.00"),
                active=True,
            ),
            FloristFoliage(
                florist_id=florist.id,
                foliage_id=fern.id,
                price=Decimal("4.00"),
                active=True,
            ),
            FloristFoliage(
                florist_id=florist.id,
                foliage_id=ruscus.id,
                price=Decimal("6.00"),
                active=False,
            ),
            FloristFoliage(
                florist_id=florist.id,
                foliage_id=olive_branch.id,
                price=Decimal("7.00"),
                active=True,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=eucalyptus.id,
                quantity=40,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=fern.id,
                quantity=0,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=ruscus.id,
                quantity=30,
            ),
            FoliageInventory(
                florist_id=florist.id,
                foliage_id=olive_branch.id,
                quantity=20,
            ),
        ]
    )
    db_session.commit()

    return SimpleNamespace(
        florist=florist,
        flowers={flower.name: flower for flower in flowers},
        foliage={item.name: item for item in foliage},
        colors=colors,
    )


def make_request(**overrides):
    data = {
        "occasion": "Birthday",
        "styles": [],
        "colors": ["Pink", "White"],
        "size": "SMALL",
    }
    data.update(overrides)
    return BouquetRequest(**data)


@pytest.mark.parametrize(
    ("size", "expected"),
    [("SMALL", (3, 7)), ("MEDIUM", (8, 14)), ("LARGE", (15, 20))],
)
def test_get_flower_quantity_range(size, expected):
    assert get_flower_quantity_range(size) == expected


def test_get_flower_quantity_range_rejects_invalid_size():
    with pytest.raises(KeyError):
        get_flower_quantity_range("XLARGE")


@pytest.mark.parametrize(
    ("size", "expected"),
    [("SMALL", 2), ("MEDIUM", 4), ("LARGE", 7)],
)
def test_get_primary_flower_quantity(size, expected):
    assert get_primary_flower_quantity(size) == expected


@pytest.mark.parametrize(
    ("size", "primary_quantity", "expected"),
    [
        ("SMALL", 2, 1),
        ("MEDIUM", 4, 4),
        ("LARGE", 7, 8),
        ("SMALL", 10, 0),
    ],
)
def test_get_remaining_quantity(size, primary_quantity, expected):
    assert get_remaining_quantity(size, primary_quantity) == expected


@pytest.mark.parametrize(
    ("size", "expected"),
    [("SMALL", 1), ("MEDIUM", 2), ("LARGE", 3)],
)
def test_get_foliage_quantity(size, expected):
    assert get_foliage_quantity(size) == expected


def test_select_primary_flower_handles_empty_candidates():
    assert select_primary_flower([]) is None


def test_select_primary_flower_returns_first_candidate():
    flowers = [
        SimpleNamespace(id=1, name="Rose"),
        SimpleNamespace(id=2, name="Tulip"),
    ]

    assert select_primary_flower(flowers) is flowers[0]


def test_prioritize_preferred_flowers_preserves_candidate_order():
    rose = SimpleNamespace(id=1, name="Rose")
    tulip = SimpleNamespace(id=2, name="Tulip")
    daisy = SimpleNamespace(id=3, name="Daisy")

    result = prioritize_preferred_flowers(
        [rose, tulip, daisy],
        ["Daisy", "Missing Flower", "Tulip"],
    )

    assert result == [tulip, daisy, rose]


def test_prioritize_preferred_flowers_handles_empty_or_missing_preferences():
    flowers = [
        SimpleNamespace(id=1, name="Rose"),
        SimpleNamespace(id=2, name="Tulip"),
    ]

    assert prioritize_preferred_flowers(flowers, []) is flowers
    assert prioritize_preferred_flowers(flowers, ["Unknown"]) == flowers


def test_add_secondary_flowers_skips_primary_and_obeys_quantity():
    rose = SimpleNamespace(id=1, name="Rose")
    tulip = SimpleNamespace(id=2, name="Tulip")
    daisy = SimpleNamespace(id=3, name="Daisy")

    result = add_secondary_flowers(
        [rose, tulip, daisy],
        rose,
        {rose.id: 2},
        1,
    )

    assert result == {rose.id: 2, tulip.id: 1}


@pytest.mark.parametrize("quantity", [0, -1])
def test_add_secondary_flowers_handles_nonpositive_quantity(quantity):
    rose = SimpleNamespace(id=1, name="Rose")
    tulip = SimpleNamespace(id=2, name="Tulip")
    composition = {rose.id: 2}

    assert add_secondary_flowers([rose, tulip], rose, composition, quantity) == {
        rose.id: 2
    }


def test_add_secondary_flowers_handles_empty_candidates():
    rose = SimpleNamespace(id=1, name="Rose")

    assert add_secondary_flowers([], rose, {rose.id: 2}, 2) == {rose.id: 2}


def test_select_foliage_handles_empty_and_zero_quantity():
    foliage = [
        SimpleNamespace(id=1, name="Eucalyptus"),
        SimpleNamespace(id=2, name="Fern"),
    ]

    assert select_foliage([], 1) == {}
    assert select_foliage(foliage, 0) == {}


def test_select_foliage_selects_no_more_than_requested():
    foliage = [
        SimpleNamespace(id=1, name="Eucalyptus"),
        SimpleNamespace(id=2, name="Fern"),
        SimpleNamespace(id=3, name="Ruscus"),
    ]

    assert select_foliage(foliage, 2) == {
        foliage[0].id: 1,
        foliage[1].id: 1,
    }


@pytest.mark.parametrize(
    ("total", "budget_max", "expected"),
    [
        (Decimal(10), None, True),
        (Decimal(10), Decimal(10), True),
        (Decimal("10.01"), Decimal(10), False),
    ],
)
def test_is_within_budget(total, budget_max, expected):
    assert is_within_budget(total, budget_max) is expected


def test_build_cheapest_composition_handles_empty_candidates():
    assert build_cheapest_composition([], "SMALL") == {}


def test_build_cheapest_composition_cycles_candidates():
    rose = SimpleNamespace(id=1, name="Rose")
    tulip = SimpleNamespace(id=2, name="Tulip")

    assert build_cheapest_composition([rose, tulip], "MEDIUM") == {
        rose.id: 4,
        tulip.id: 4,
    }


def test_database_stock_helpers_return_inventory_or_zero(db_session, catalog):
    rose = catalog.flowers["Rose"]
    eucalyptus = catalog.foliage["Eucalyptus"]

    assert get_flower_stock(db_session, catalog.florist.id, rose.id) == 30
    assert get_foliage_stock(db_session, catalog.florist.id, eucalyptus.id) == 40
    assert get_flower_stock(db_session, catalog.florist.id, 99999) == 0
    assert get_foliage_stock(db_session, catalog.florist.id, 99999) == 0


def test_sufficient_flower_stock_checks_every_item(db_session, catalog):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]
    florist_id = catalog.florist.id

    assert has_sufficient_stock(db_session, florist_id, {})
    assert has_sufficient_stock(db_session, florist_id, {rose.id: 30, tulip.id: 25})
    assert not has_sufficient_stock(db_session, florist_id, {rose.id: 31})
    assert not has_sufficient_stock(db_session, florist_id, {99999: 1})


def test_sufficient_foliage_stock_checks_every_item(db_session, catalog):
    eucalyptus = catalog.foliage["Eucalyptus"]
    fern = catalog.foliage["Fern"]
    florist_id = catalog.florist.id

    assert has_sufficient_foliage_stock(db_session, florist_id, {})
    assert has_sufficient_foliage_stock(
        db_session,
        florist_id,
        {eucalyptus.id: 40},
    )
    assert not has_sufficient_foliage_stock(
        db_session,
        florist_id,
        {eucalyptus.id: 41},
    )
    assert not has_sufficient_foliage_stock(
        db_session,
        florist_id,
        {fern.id: 1},
    )


def test_calculate_bouquet_price_uses_active_florist_prices(db_session, catalog):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]

    total = calculate_bouquet_price(
        db_session,
        catalog.florist.id,
        {rose.id: 2, tulip.id: 1},
    )

    assert total == Decimal("32.00")
    assert calculate_bouquet_price(db_session, catalog.florist.id, {}) == Decimal(
        0
    )
    assert calculate_bouquet_price(
        db_session,
        catalog.florist.id,
        {99999: 1},
    ) == Decimal(0)


def test_sort_flowers_by_price_returns_ascending_prices(db_session, catalog):
    flowers = [
        catalog.flowers["Rose"],
        catalog.flowers["Tulip"],
        catalog.flowers["Daisy"],
    ]

    result = sort_flowers_by_price(db_session, catalog.florist.id, flowers)

    assert [flower.name for flower in result] == ["Daisy", "Tulip", "Rose"]
    assert sort_flowers_by_price(db_session, catalog.florist.id, []) == []


def test_validate_composition_checks_stock_and_budget(db_session, catalog):
    rose = catalog.flowers["Rose"]
    florist_id = catalog.florist.id

    assert not validate_composition(db_session, florist_id, {}, None)
    assert validate_composition(
        db_session,
        florist_id,
        {rose.id: 2},
        Decimal("24.00"),
    )
    assert validate_composition(db_session, florist_id, {rose.id: 2}, None)
    assert not validate_composition(
        db_session,
        florist_id,
        {rose.id: 2},
        Decimal("23.99"),
    )
    assert not validate_composition(db_session, florist_id, {rose.id: 31}, None)


def test_find_candidate_flowers_filters_and_deduplicates(db_session, catalog):
    request = make_request(colors=["Pink", "White"])

    result = find_candidate_flowers(db_session, catalog.florist.id, request)
    names = [flower.name for flower in result]

    assert set(names) == {"Rose", "Tulip", "Daisy"}
    assert len(names) == len(set(names))


def test_find_candidate_flowers_applies_styles_and_exclusions(
    db_session,
    catalog,
):
    request = make_request(
        styles=["Romantic"],
        excluded_flowers=["Rose"],
    )

    result = find_candidate_flowers(db_session, catalog.florist.id, request)

    assert [flower.name for flower in result] == ["Daisy"]


@pytest.mark.parametrize(
    "request_overrides",
    [
        {"occasion": "Unknown Occasion"},
        {"styles": ["Unknown Style"]},
        {"colors": ["Unknown Color"]},
        {"excluded_flowers": ["Rose", "Tulip", "Daisy", "Lily"]},
    ],
)
def test_find_candidate_flowers_returns_empty_when_filters_match_nothing(
    db_session,
    catalog,
    request_overrides,
):
    request = make_request(**request_overrides)

    assert find_candidate_flowers(db_session, catalog.florist.id, request) == []


def test_find_candidate_flowers_returns_empty_for_unknown_florist(
    db_session,
    catalog,
):
    request = make_request()

    assert find_candidate_flowers(db_session, 99999, request) == []


def test_find_candidate_foliage_requires_active_catalog_and_positive_stock(
    db_session,
    catalog,
):
    result = find_candidate_foliage(db_session, catalog.florist.id)

    assert {item.name for item in result} == {"Eucalyptus", "Olive Branch"}
    assert find_candidate_foliage(db_session, 99999) == []


def test_find_valid_composition_prioritizes_preferred_flowers(
    db_session,
    catalog,
):
    flowers = [
        catalog.flowers["Rose"],
        catalog.flowers["Tulip"],
        catalog.flowers["Daisy"],
    ]

    composition = find_valid_composition(
        db_session,
        catalog.florist.id,
        flowers,
        "SMALL",
        None,
        ["Tulip"],
    )

    assert composition == {
        catalog.flowers["Tulip"].id: 2,
        catalog.flowers["Rose"].id: 1,
    }


def test_find_valid_composition_falls_back_to_cheaper_mix(
    db_session,
    catalog,
):
    flowers = [
        catalog.flowers["Rose"],
        catalog.flowers["Tulip"],
        catalog.flowers["Daisy"],
    ]

    composition = find_valid_composition(
        db_session,
        catalog.florist.id,
        flowers,
        "SMALL",
        Decimal("26.00"),
        ["Rose"],
    )

    assert composition == {
        catalog.flowers["Daisy"].id: 1,
        catalog.flowers["Tulip"].id: 1,
        catalog.flowers["Rose"].id: 1,
    }


def test_find_valid_composition_handles_empty_and_unavailable_candidates(
    db_session,
    catalog,
):
    assert find_valid_composition(
        db_session,
        catalog.florist.id,
        [],
        "SMALL",
        None,
        [],
    ) == {}

    rose = catalog.flowers["Rose"]
    inventory = db_session.get(
        FlowerInventory,
        (catalog.florist.id, rose.id),
    )
    inventory.quantity = 1
    db_session.flush()

    assert find_valid_composition(
        db_session,
        catalog.florist.id,
        [rose],
        "SMALL",
        None,
        [],
    ) == {}


def test_find_valid_composition_rejects_insufficient_budget(db_session, catalog):
    flowers = [
        catalog.flowers["Rose"],
        catalog.flowers["Tulip"],
        catalog.flowers["Daisy"],
    ]

    assert find_valid_composition(
        db_session,
        catalog.florist.id,
        flowers,
        "SMALL",
        Decimal("1.00"),
        [],
    ) == {}


def test_find_valid_composition_rejects_invalid_size(db_session, catalog):
    with pytest.raises(KeyError):
        find_valid_composition(
            db_session,
            catalog.florist.id,
            [catalog.flowers["Rose"]],
            "EXTRA_LARGE",
            None,
            [],
        )