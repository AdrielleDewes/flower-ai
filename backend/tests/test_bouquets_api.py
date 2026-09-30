from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import Florist, FloristFlower, Flower, FlowerInventory


@pytest.fixture
def api_client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def florist_with_flower(db_session: Session) -> tuple[Florist, Flower]:
    florist = Florist(name="Test Florist")
    flower = Flower(name="Rose")
    db_session.add_all([florist, flower])
    db_session.flush()
    db_session.add(
        FloristFlower(
            florist_id=florist.id,
            flower_id=flower.id,
            price=12,
            active=True,
        )
    )
    db_session.add(
        FlowerInventory(
            florist_id=florist.id,
            flower_id=flower.id,
            quantity=1,
        )
    )
    db_session.flush()
    return florist, flower


def test_create_bouquet_returns_400_for_item_not_offered(
    api_client,
    db_session,
):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()

    response = api_client.post(
        f"/florists/{florist.id}/bouquets/",
        json={
            "name": "Invalid Bouquet",
            "size": "SMALL",
            "source": "MANUAL",
            "flowers": {999: 1},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Bouquet contains items not offered by the florist."
    )


def test_create_bouquet_returns_400_for_nonpositive_quantity(
    api_client,
    florist_with_flower,
):
    florist, flower = florist_with_flower

    response = api_client.post(
        f"/florists/{florist.id}/bouquets/",
        json={
            "name": "Invalid Quantity Bouquet",
            "size": "SMALL",
            "source": "MANUAL",
            "flowers": {flower.id: 0},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Bouquet item quantities must be greater than zero."
    )


def test_create_bouquet_returns_400_for_insufficient_stock(
    api_client,
    florist_with_flower,
):
    florist, flower = florist_with_flower

    response = api_client.post(
        f"/florists/{florist.id}/bouquets/",
        json={
            "name": "Out of Stock Bouquet",
            "size": "SMALL",
            "source": "MANUAL",
            "flowers": {flower.id: 2},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Not enough stock for flower {flower.id}."


def test_update_bouquet_replaces_saved_bouquet(
    api_client,
    florist_with_flower,
):
    florist, flower = florist_with_flower
    created = api_client.post(
        f"/florists/{florist.id}/bouquets/",
        json={
            "name": "Original Bouquet",
            "size": "SMALL",
            "source": "MANUAL",
            "flowers": {flower.id: 1},
        },
    )
    bouquet_id = created.json()["id"]

    response = api_client.patch(
        f"/florists/{florist.id}/bouquets/{bouquet_id}",
        json={
            "name": "Updated Bouquet",
            "description": "Updated through the API",
            "size": "MEDIUM",
            "flowers": {flower.id: 1},
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Bouquet"
    assert response.json()["description"] == "Updated through the API"
    assert response.json()["size"] == "MEDIUM"
    assert response.json()["source"] == "MANUAL"

    detail = api_client.get(
        f"/florists/{florist.id}/bouquets/{bouquet_id}"
    )
    assert detail.status_code == 200
    assert detail.json()["flowers"] == [
        {"id": flower.id, "name": flower.name, "quantity": 1}
    ]


def test_update_bouquet_returns_404_when_not_owned_by_florist(
    api_client,
    db_session,
    florist_with_flower,
):
    florist, _flower = florist_with_flower
    other_florist = Florist(name="Other Florist")
    db_session.add(other_florist)
    db_session.flush()

    created = api_client.post(
        f"/florists/{florist.id}/bouquets/",
        json={
            "name": "Private Bouquet",
            "size": "SMALL",
            "source": "MANUAL",
        },
    )
    bouquet_id = created.json()["id"]

    response = api_client.patch(
        f"/florists/{other_florist.id}/bouquets/{bouquet_id}",
        json={
            "name": "Unauthorized update",
            "size": "SMALL",
            "source": "MANUAL",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Bouquet not found."


def test_delete_bouquet_returns_204_and_deletes_its_composition(
    api_client,
    florist_with_flower,
):
    florist, flower = florist_with_flower
    created = api_client.post(
        f"/florists/{florist.id}/bouquets/",
        json={
            "name": "Bouquet to delete",
            "size": "SMALL",
            "source": "MANUAL",
            "flowers": {flower.id: 1},
        },
    )
    bouquet_id = created.json()["id"]

    response = api_client.delete(
        f"/florists/{florist.id}/bouquets/{bouquet_id}"
    )

    assert response.status_code == 204
    assert response.content == b""
    assert api_client.get(
        f"/florists/{florist.id}/bouquets/{bouquet_id}"
    ).status_code == 404
