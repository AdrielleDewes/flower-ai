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
