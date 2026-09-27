from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.models import (
    Color,
    Florist,
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
from app.services.recommendation import (
    add_secondary_flowers,
    build_cheapest_composition,
    build_complete_composition,
    build_preferred_flower_composition,
    build_recommended_composition,
    calculate_bouquet_price,
    calculate_complete_bouquet_price,
    calculate_foliage_price,
    calculate_wrapping_price,
    find_candidate_flowers,
    find_candidate_foliage,
    find_candidate_wrappings,
    find_valid_composition,
    get_flower_quantity_range,
    get_flower_stock,
    get_foliage_quantity,
    get_foliage_stock,
    get_primary_flower_quantity,
    get_remaining_quantity,
    get_wrapping_stock,
    has_sufficient_foliage_stock,
    has_sufficient_stock,
    has_sufficient_wrapping_stock,
    is_within_budget,
    prioritize_preferred_flowers,
    select_foliage,
    select_primary_flower,
    select_wrapping,
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


def test_add_secondary_flowers_skips_primary_and_obeys_quantity(
    db_session,
    catalog,
):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]
    daisy = catalog.flowers["Daisy"]

    result = add_secondary_flowers(
        db_session,
        catalog.florist.id,
        [rose, tulip, daisy],
        rose,
        {rose.id: 2},
        1,
    )

    assert result == {rose.id: 2, tulip.id: 1}


@pytest.mark.parametrize("quantity", [0, -1])
def test_add_secondary_flowers_handles_nonpositive_quantity(
    db_session,
    catalog,
    quantity,
):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]
    composition = {rose.id: 2}

    assert add_secondary_flowers(
        db_session,
        catalog.florist.id,
        [rose, tulip],
        rose,
        composition,
        quantity,
    ) == {rose.id: 2}


def test_add_secondary_flowers_handles_empty_candidates(db_session, catalog):
    rose = catalog.flowers["Rose"]

    assert add_secondary_flowers(
        db_session,
        catalog.florist.id,
        [],
        rose,
        {rose.id: 2},
        2,
    ) == {rose.id: 2}


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


def test_build_cheapest_composition_handles_empty_candidates(db_session, catalog):
    assert build_cheapest_composition(
        db_session,
        catalog.florist.id,
        [],
        "SMALL",
    ) == {}


def test_build_cheapest_composition_uses_stock_to_meet_minimum(
    db_session,
    catalog,
):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]

    assert build_cheapest_composition(
        db_session,
        catalog.florist.id,
        [rose, tulip],
        "MEDIUM",
    ) == {
        rose.id: 8,
    }


def test_build_preferred_flower_composition_limits_primary_to_stock(
    db_session,
    catalog,
):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]
    db_session.get(FlowerInventory, (catalog.florist.id, rose.id)).quantity = 1
    db_session.get(FlowerInventory, (catalog.florist.id, tulip.id)).quantity = 2
    db_session.flush()

    assert build_preferred_flower_composition(
        db_session,
        catalog.florist.id,
        [rose, tulip],
        rose,
        "SMALL",
    ) == {rose.id: 1, tulip.id: 2}


def test_build_preferred_flower_composition_requires_minimum_stock(
    db_session,
    catalog,
):
    rose = catalog.flowers["Rose"]
    tulip = catalog.flowers["Tulip"]
    db_session.get(FlowerInventory, (catalog.florist.id, rose.id)).quantity = 1
    db_session.get(FlowerInventory, (catalog.florist.id, tulip.id)).quantity = 1
    db_session.flush()

    assert build_preferred_flower_composition(
        db_session,
        catalog.florist.id,
        [rose, tulip],
        rose,
        "SMALL",
    ) == {}


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


def test_wrapping_stock_helpers_check_available_quantity(db_session, catalog):
    kraft_paper = Wrapping(name="Kraft Paper")
    db_session.add(kraft_paper)
    db_session.flush()
    db_session.add(
        WrappingInventory(
            florist_id=catalog.florist.id,
            wrapping_id=kraft_paper.id,
            quantity=50,
        )
    )
    db_session.commit()

    florist_id = catalog.florist.id

    assert get_wrapping_stock(db_session, florist_id, kraft_paper.id) == 50
    assert get_wrapping_stock(db_session, florist_id, 99999) == 0
    assert has_sufficient_wrapping_stock(db_session, florist_id, {})
    assert has_sufficient_wrapping_stock(
        db_session,
        florist_id,
        {kraft_paper.id: 50},
    )
    assert not has_sufficient_wrapping_stock(
        db_session,
        florist_id,
        {kraft_paper.id: 51},
    )
    assert not has_sufficient_wrapping_stock(
        db_session,
        florist_id,
        {99999: 1},
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


def test_calculate_foliage_price_uses_active_florist_prices(db_session, catalog):
    eucalyptus = catalog.foliage["Eucalyptus"]
    fern = catalog.foliage["Fern"]
    inactive_ruscus = catalog.foliage["Ruscus"]

    total = calculate_foliage_price(
        db_session,
        catalog.florist.id,
        {
            eucalyptus.id: 2,
            fern.id: 1,
            inactive_ruscus.id: 4,
            99999: 3,
        },
    )

    assert total == Decimal("14.00")
    assert calculate_foliage_price(db_session, catalog.florist.id, {}) == Decimal(0)


def test_calculate_wrapping_price_uses_active_florist_prices(db_session, catalog):
    kraft_paper = Wrapping(name="Kraft Paper")
    inactive_paper = Wrapping(name="Inactive Paper")
    db_session.add_all([kraft_paper, inactive_paper])
    db_session.flush()
    db_session.add_all(
        [
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=kraft_paper.id,
                price=Decimal("4.00"),
                active=True,
            ),
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=inactive_paper.id,
                price=Decimal("12.00"),
                active=False,
            ),
        ]
    )
    db_session.commit()

    total = calculate_wrapping_price(
        db_session,
        catalog.florist.id,
        {kraft_paper.id: 2, inactive_paper.id: 1, 99999: 1},
    )

    assert total == Decimal("8.00")
    assert calculate_wrapping_price(db_session, catalog.florist.id, {}) == Decimal(0)


def test_calculate_complete_bouquet_price_sums_all_components(db_session, catalog):
    rose = catalog.flowers["Rose"]
    eucalyptus = catalog.foliage["Eucalyptus"]
    kraft_paper = Wrapping(name="Kraft Paper")
    db_session.add(kraft_paper)
    db_session.flush()
    db_session.add(
        FloristWrapping(
            florist_id=catalog.florist.id,
            wrapping_id=kraft_paper.id,
            price=Decimal("4.00"),
            active=True,
        )
    )
    db_session.commit()

    total = calculate_complete_bouquet_price(
        db_session,
        catalog.florist.id,
        {
            "flowers": {rose.id: 2},
            "foliage": {eucalyptus.id: 2},
            "wrapping": {kraft_paper.id: 3},
        },
    )

    assert total == Decimal("46.00")
    assert calculate_complete_bouquet_price(
        db_session,
        catalog.florist.id,
        {"flowers": {}, "foliage": {}, "wrapping": {}},
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
    eucalyptus = catalog.foliage["Eucalyptus"]
    kraft_paper = Wrapping(name="Kraft Paper")
    db_session.add(kraft_paper)
    db_session.flush()
    db_session.add_all(
        [
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=kraft_paper.id,
                price=Decimal("4.00"),
                active=True,
            ),
            WrappingInventory(
                florist_id=catalog.florist.id,
                wrapping_id=kraft_paper.id,
                quantity=5,
            ),
        ]
    )
    db_session.commit()

    florist_id = catalog.florist.id
    composition = {
        "flowers": {rose.id: 2},
        "foliage": {eucalyptus.id: 2},
        "wrapping": {kraft_paper.id: 1},
    }

    assert not validate_composition(db_session, florist_id, {}, None)
    assert validate_composition(
        db_session,
        florist_id,
        composition,
        Decimal("38.00"),
    )
    assert validate_composition(db_session, florist_id, composition, None)
    assert not validate_composition(
        db_session,
        florist_id,
        composition,
        Decimal("37.99"),
    )
    insufficient_flower_stock = {
        **composition,
        "flowers": {rose.id: 31},
    }
    assert not validate_composition(
        db_session,
        florist_id,
        insufficient_flower_stock,
        None,
    )
    insufficient_foliage_stock = {
        **composition,
        "foliage": {eucalyptus.id: 41},
    }
    assert not validate_composition(
        db_session,
        florist_id,
        insufficient_foliage_stock,
        None,
    )
    insufficient_wrapping_stock = {
        **composition,
        "wrapping": {kraft_paper.id: 6},
    }
    assert not validate_composition(
        db_session,
        florist_id,
        insufficient_wrapping_stock,
        None,
    )


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


def test_find_candidate_wrappings_requires_active_catalog_and_positive_stock(
    db_session,
    catalog,
):
    active = Wrapping(name="Kraft Paper")
    out_of_stock = Wrapping(name="Out Of Stock Paper")
    inactive = Wrapping(name="Inactive Paper")
    other_florist_only = Wrapping(name="Other Florist Paper")
    other_florist = Florist(name="Other Florist")

    db_session.add_all(
        [active, out_of_stock, inactive, other_florist_only, other_florist]
    )
    db_session.flush()

    db_session.add_all(
        [
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=active.id,
                price=Decimal("4.00"),
                active=True,
            ),
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=out_of_stock.id,
                price=Decimal("4.00"),
                active=True,
            ),
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=inactive.id,
                price=Decimal("4.00"),
                active=False,
            ),
            FloristWrapping(
                florist_id=other_florist.id,
                wrapping_id=other_florist_only.id,
                price=Decimal("4.00"),
                active=True,
            ),
            WrappingInventory(
                florist_id=catalog.florist.id,
                wrapping_id=active.id,
                quantity=10,
            ),
            WrappingInventory(
                florist_id=catalog.florist.id,
                wrapping_id=out_of_stock.id,
                quantity=0,
            ),
            WrappingInventory(
                florist_id=catalog.florist.id,
                wrapping_id=inactive.id,
                quantity=10,
            ),
            WrappingInventory(
                florist_id=other_florist.id,
                wrapping_id=other_florist_only.id,
                quantity=10,
            ),
        ]
    )
    db_session.commit()

    candidates = find_candidate_wrappings(db_session, catalog.florist.id)

    assert [wrapping.name for wrapping in candidates] == ["Kraft Paper"]
    assert find_candidate_wrappings(db_session, 99999) == []


def test_select_wrapping_returns_none_for_empty_candidates():
    assert select_wrapping([]) is None


def test_select_wrapping_returns_first_candidate():
    wrappings = [
        SimpleNamespace(id=1, name="Kraft Paper"),
        SimpleNamespace(id=2, name="White Paper"),
    ]

    assert select_wrapping(wrappings) is wrappings[0]


def test_build_complete_composition_includes_wrapping():
    flowers = {1: 3}
    foliage = {8: 1}
    wrapping = SimpleNamespace(id=12)

    assert build_complete_composition(flowers, foliage, wrapping) == {
        "flowers": flowers,
        "foliage": foliage,
        "wrapping": {12: 1},
    }


def test_build_complete_composition_handles_missing_wrapping():
    flowers = {1: 3}
    foliage = {8: 1}

    assert build_complete_composition(flowers, foliage, None) == {
        "flowers": flowers,
        "foliage": foliage,
        "wrapping": {},
    }


def test_build_recommended_composition_selects_available_foliage_without_wrapping(
    db_session,
    catalog,
):
    flowers = {catalog.flowers["Rose"].id: 4}

    composition = build_recommended_composition(
        db_session,
        catalog.florist.id,
        flowers,
        "MEDIUM",
    )

    expected_foliage_ids = {
        catalog.foliage["Eucalyptus"].id,
        catalog.foliage["Olive Branch"].id,
    }
    assert composition == {
        "flowers": flowers,
        "foliage": {foliage_id: 1 for foliage_id in expected_foliage_ids},
        "wrapping": {},
    }


def test_build_recommended_composition_includes_available_wrapping(
    db_session,
    catalog,
):
    wrapping = Wrapping(name="Kraft Paper")
    db_session.add(wrapping)
    db_session.flush()
    db_session.add_all(
        [
            FloristWrapping(
                florist_id=catalog.florist.id,
                wrapping_id=wrapping.id,
                price=Decimal("4.00"),
                active=True,
            ),
            WrappingInventory(
                florist_id=catalog.florist.id,
                wrapping_id=wrapping.id,
                quantity=10,
            ),
        ]
    )
    db_session.commit()

    flowers = {catalog.flowers["Rose"].id: 2}
    composition = build_recommended_composition(
        db_session,
        catalog.florist.id,
        flowers,
        "SMALL",
    )

    assert composition["flowers"] == flowers
    assert composition["wrapping"] == {wrapping.id: 1}


def test_build_recommended_composition_handles_no_available_accessories(
    db_session,
    catalog,
):
    flowers = {catalog.flowers["Rose"].id: 2}

    composition = build_recommended_composition(
        db_session,
        99999,
        flowers,
        "SMALL",
    )

    assert composition == {
        "flowers": flowers,
        "foliage": {},
        "wrapping": {},
    }


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
        "flowers": {
            catalog.flowers["Tulip"].id: 2,
            catalog.flowers["Rose"].id: 1,
        },
        "foliage": {catalog.foliage["Eucalyptus"].id: 1},
        "wrapping": {},
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
        Decimal("31.00"),
        ["Rose"],
    )

    assert composition == {
        "flowers": {
            catalog.flowers["Daisy"].id: 3,
        },
        "foliage": {catalog.foliage["Eucalyptus"].id: 1},
        "wrapping": {},
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
