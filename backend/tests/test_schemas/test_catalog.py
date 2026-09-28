from decimal import Decimal

from app.schemas.catalog import CatalogResponse
from app.schemas.flower import FlowerResponse
from app.schemas.foliage import FoliageResponse
from app.schemas.wrapping import WrappingResponse


def test_catalog_response_validates_all_catalog_item_types():
    catalog = CatalogResponse(
        flowers=[
            {
                "id": 1,
                "name": "Rose",
                "description": None,
                "price": "12.00",
                "available_quantity": 10,
                "active": True,
            }
        ],
        foliage=[
            {
                "id": 2,
                "name": "Eucalyptus",
                "description": None,
                "price": "5.00",
                "available_quantity": 20,
                "active": True,
            }
        ],
        wrappings=[
            {
                "id": 3,
                "name": "Kraft Paper",
                "description": None,
                "price": "4.00",
                "available_quantity": 15,
                "active": True,
            }
        ],
    )

    assert isinstance(catalog.flowers[0], FlowerResponse)
    assert isinstance(catalog.foliage[0], FoliageResponse)
    assert isinstance(catalog.wrappings[0], WrappingResponse)
    assert catalog.flowers[0].price == Decimal("12.00")
    assert catalog.foliage[0].price == Decimal("5.00")
    assert catalog.wrappings[0].price == Decimal("4.00")
