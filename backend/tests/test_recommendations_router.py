from decimal import Decimal
from types import SimpleNamespace

from app.schemas.bouquet import BouquetRequest
from app.schemas.recommendation import Recommendation
from app.routers import recommendations


def test_create_recommendation_uses_injected_florist_id(db_session, monkeypatch):
    florist = SimpleNamespace(id=42)
    request = BouquetRequest(
        occasion="Birthday",
        styles=[],
        colors=["Pink"],
        size="SMALL",
    )
    expected = Recommendation(
        flowers=[],
        foliage=[],
        wrapping=[],
        total_price=Decimal("25.00"),
    )
    calls = {}

    def fake_generate_recommendation(db, *, florist_id, request):
        calls["db"] = db
        calls["florist_id"] = florist_id
        calls["request"] = request
        return expected

    monkeypatch.setattr(
        recommendations,
        "generate_recommendation",
        fake_generate_recommendation,
    )

    result = recommendations.create_recommendation(
        request=request,
        florist=florist,
        db=db_session,
    )

    assert result is expected
    assert calls == {
        "db": db_session,
        "florist_id": florist.id,
        "request": request,
    }
