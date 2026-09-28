from types import SimpleNamespace

from app.routers import wrappings


def test_list_wrappings_uses_injected_florist_id(db_session, monkeypatch):
    florist = SimpleNamespace(id=42)
    expected = [{"id": 1, "name": "Kraft Paper"}]
    calls = {}

    def fake_get_florist_wrappings(db, florist_id):
        calls["db"] = db
        calls["florist_id"] = florist_id
        return expected

    monkeypatch.setattr(
        wrappings,
        "get_florist_wrappings",
        fake_get_florist_wrappings,
    )

    result = wrappings.list_wrappings(florist=florist, db=db_session)

    assert result is expected
    assert calls == {"db": db_session, "florist_id": florist.id}
