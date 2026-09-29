from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.routers import bouquets
from app.schemas.bouquet import BouquetCreate, BouquetSize


def test_create_bouquet_endpoint_uses_injected_florist_id(
    db_session,
    monkeypatch,
):
    florist = SimpleNamespace(id=42)
    bouquet_data = BouquetCreate(
        name="Birthday Bouquet",
        size=BouquetSize.SMALL,
        source="MANUAL",
    )
    expected = SimpleNamespace(id=10)
    calls = {}

    def fake_create_bouquet(db, florist_id, requested_bouquet_data):
        calls["db"] = db
        calls["florist_id"] = florist_id
        calls["bouquet_data"] = requested_bouquet_data
        return expected

    monkeypatch.setattr(bouquets, "create_bouquet", fake_create_bouquet)

    result = bouquets.create_bouquet_endpoint(
        bouquet_data=bouquet_data,
        florist=florist,
        db=db_session,
    )

    assert result is expected
    assert calls == {
        "db": db_session,
        "florist_id": florist.id,
        "bouquet_data": bouquet_data,
    }


def test_create_bouquet_endpoint_returns_400_for_validation_error(
    db_session,
    monkeypatch,
):
    florist = SimpleNamespace(id=42)
    bouquet_data = BouquetCreate(
        name="Invalid Bouquet",
        size=BouquetSize.SMALL,
        source="MANUAL",
    )

    def reject_bouquet(*_args):
        raise ValueError("Not enough stock for flower 1.")

    monkeypatch.setattr(bouquets, "create_bouquet", reject_bouquet)

    with pytest.raises(HTTPException) as exc_info:
        bouquets.create_bouquet_endpoint(
            bouquet_data=bouquet_data,
            florist=florist,
            db=db_session,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Not enough stock for flower 1."
