from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.routers import bouquets
from app.schemas.bouquet import BouquetCreate, BouquetSize, BouquetUpdate


def test_list_bouquets_uses_injected_florist_id(db_session, monkeypatch):
    florist = SimpleNamespace(id=42)
    expected = [SimpleNamespace(id=10)]
    calls = {}

    def fake_get_florist_bouquets(db, florist_id):
        calls["db"] = db
        calls["florist_id"] = florist_id
        return expected

    monkeypatch.setattr(
        bouquets,
        "get_florist_bouquets",
        fake_get_florist_bouquets,
    )

    result = bouquets.list_bouquets(florist=florist, db=db_session)

    assert result is expected
    assert calls == {"db": db_session, "florist_id": florist.id}


def test_get_bouquet_uses_injected_florist_and_bouquet_ids(
    db_session,
    monkeypatch,
):
    florist = SimpleNamespace(id=42)
    expected = {"id": 10, "flowers": [], "foliage": [], "wrapping": []}
    calls = {}

    def fake_get_bouquet_detail(db, florist_id, bouquet_id):
        calls["db"] = db
        calls["florist_id"] = florist_id
        calls["bouquet_id"] = bouquet_id
        return expected

    monkeypatch.setattr(
        bouquets,
        "get_bouquet_detail",
        fake_get_bouquet_detail,
    )

    result = bouquets.get_bouquet(
        bouquet_id=10,
        florist=florist,
        db=db_session,
    )

    assert result is expected
    assert calls == {
        "db": db_session,
        "florist_id": florist.id,
        "bouquet_id": 10,
    }


def test_get_bouquet_returns_404_when_bouquet_is_missing(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        bouquets,
        "get_bouquet_detail",
        lambda *_args: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        bouquets.get_bouquet(
            bouquet_id=10,
            florist=SimpleNamespace(id=42),
            db=db_session,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Bouquet not found."


def test_update_bouquet_endpoint_uses_validated_florist(
    db_session,
    monkeypatch,
):
    florist = SimpleNamespace(id=42)
    bouquet_data = BouquetUpdate(
        name="Updated Bouquet",
        size=BouquetSize.SMALL,
    )
    expected = SimpleNamespace(id=10)
    calls = {}

    def fake_update_bouquet(db, florist_id, bouquet_id, data):
        calls.update(
            db=db,
            florist_id=florist_id,
            bouquet_id=bouquet_id,
            bouquet_data=data,
        )
        return expected

    monkeypatch.setattr(bouquets, "update_bouquet", fake_update_bouquet)

    result = bouquets.update_bouquet_endpoint(
        bouquet_id=10,
        bouquet_data=bouquet_data,
        florist=florist,
        db=db_session,
    )

    assert result is expected
    assert calls == {
        "db": db_session,
        "florist_id": florist.id,
        "bouquet_id": 10,
        "bouquet_data": bouquet_data,
    }


@pytest.mark.parametrize(
    ("service_result", "expected_status", "expected_detail"),
    [
        (None, status.HTTP_404_NOT_FOUND, "Bouquet not found."),
        (
            ValueError("Bouquet item quantities must be greater than zero."),
            status.HTTP_400_BAD_REQUEST,
            "Bouquet item quantities must be greater than zero.",
        ),
    ],
)
def test_update_bouquet_endpoint_maps_expected_errors(
    db_session,
    monkeypatch,
    service_result,
    expected_status,
    expected_detail,
):
    def fake_update_bouquet(*_args):
        if isinstance(service_result, Exception):
            raise service_result
        return service_result

    monkeypatch.setattr(bouquets, "update_bouquet", fake_update_bouquet)

    with pytest.raises(HTTPException) as exc_info:
        bouquets.update_bouquet_endpoint(
            bouquet_id=10,
            bouquet_data=BouquetUpdate(
                name="Updated Bouquet",
                size=BouquetSize.SMALL,
            ),
            florist=SimpleNamespace(id=42),
            db=db_session,
        )

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


def test_delete_bouquet_endpoint_uses_florist_and_bouquet_ids(
    db_session,
    monkeypatch,
):
    florist = SimpleNamespace(id=42)
    calls = {}

    def fake_delete_bouquet(db, florist_id, bouquet_id):
        calls.update(db=db, florist_id=florist_id, bouquet_id=bouquet_id)
        return True

    monkeypatch.setattr(bouquets, "delete_bouquet", fake_delete_bouquet)

    result = bouquets.delete_bouquet_endpoint(
        bouquet_id=10,
        florist=florist,
        db=db_session,
    )

    assert result is None
    assert calls == {
        "db": db_session,
        "florist_id": florist.id,
        "bouquet_id": 10,
    }


def test_delete_bouquet_endpoint_returns_404_when_missing(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(bouquets, "delete_bouquet", lambda *_args: False)

    with pytest.raises(HTTPException) as exc_info:
        bouquets.delete_bouquet_endpoint(
            bouquet_id=10,
            florist=SimpleNamespace(id=42),
            db=db_session,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Bouquet not found."


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
