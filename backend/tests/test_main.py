from app.main import app


def test_recommendations_router_is_included_in_application():
    paths = app.openapi()["paths"]

    assert "post" in paths["/florists/{florist_id}/recommendations"]


def test_bouquets_router_is_included_in_application():
    paths = app.openapi()["paths"]

    assert "post" in paths["/florists/{florist_id}/bouquets/"]


def test_flowers_router_is_included_in_application():
    paths = app.openapi()["paths"]

    assert "get" in paths["/florists/{florist_id}/flowers/"]


def test_foliage_router_is_included_in_application():
    paths = app.openapi()["paths"]

    assert "get" in paths["/florists/{florist_id}/foliage/"]


def test_wrappings_router_is_included_in_application():
    paths = app.openapi()["paths"]

    assert "get" in paths["/florists/{florist_id}/wrappings/"]


def test_root_status_route_remains_available():
    paths = app.openapi()["paths"]

    assert "get" in paths["/"]
