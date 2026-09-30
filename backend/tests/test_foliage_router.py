from types import SimpleNamespace

from app.routers import foliage


def test_list_foliage_uses_injected_florist_id(db_session, monkeypatch):
    florist = SimpleNamespace(id=42)
    expected = [{"id": 1, "name": "Eucalyptus"}]
    calls = {}

    def fake_get_florist_foliage(db, florist_id):
        calls["db"] = db
        calls["florist_id"] = florist_id
        return expected

    monkeypatch.setattr(
        foliage,
        "get_florist_foliage",
        fake_get_florist_foliage,
    )

    result = foliage.list_foliage(florist=florist, db=db_session)

    assert result is expected
    assert calls == {"db": db_session, "florist_id": florist.id}
