from app.services import catalog


def test_get_florist_catalog_combines_catalog_services(db_session, monkeypatch):
    florist_id = 42
    calls = []
    flowers = [{"id": 1, "name": "Rose"}]
    foliage = [{"id": 2, "name": "Eucalyptus"}]
    wrappings = [{"id": 3, "name": "Kraft Paper"}]

    def fake_get_florist_flowers(db, requested_florist_id):
        calls.append(("flowers", db, requested_florist_id))
        return flowers

    def fake_get_florist_foliage(db, requested_florist_id):
        calls.append(("foliage", db, requested_florist_id))
        return foliage

    def fake_get_florist_wrappings(db, requested_florist_id):
        calls.append(("wrappings", db, requested_florist_id))
        return wrappings

    monkeypatch.setattr(catalog, "get_florist_flowers", fake_get_florist_flowers)
    monkeypatch.setattr(catalog, "get_florist_foliage", fake_get_florist_foliage)
    monkeypatch.setattr(
        catalog,
        "get_florist_wrappings",
        fake_get_florist_wrappings,
    )

    result = catalog.get_florist_catalog(db_session, florist_id)

    assert result == {
        "flowers": flowers,
        "foliage": foliage,
        "wrappings": wrappings,
    }
    assert calls == [
        ("flowers", db_session, florist_id),
        ("foliage", db_session, florist_id),
        ("wrappings", db_session, florist_id),
    ]
