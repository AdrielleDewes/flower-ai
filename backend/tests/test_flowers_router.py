from types import SimpleNamespace

from app.routers import flowers


def test_list_flowers_uses_injected_florist_id(db_session, monkeypatch):
    florist = SimpleNamespace(id=42)
    expected = [{"id": 1, "name": "Rose"}]
    calls = {}

    def fake_get_florist_flowers(db, florist_id):
        calls["db"] = db
        calls["florist_id"] = florist_id
        return expected

    monkeypatch.setattr(flowers, "get_florist_flowers", fake_get_florist_flowers)

    result = flowers.list_flowers(florist=florist, db=db_session)

    assert result is expected
    assert calls == {"db": db_session, "florist_id": florist.id}
