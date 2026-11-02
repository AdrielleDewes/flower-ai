"""POC HTTP flow with local test DB and fake providers; no model inference."""

import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.dependencies import get_interpretation_provider
from app.main import app
from app.models import (
    Bouquet,
    Color,
    Florist,
    FloristFlower,
    FloristFoliage,
    FloristWrapping,
    Flower,
    FlowerColor,
    FlowerInventory,
    FlowerOccasion,
    FlowerStyle,
    Foliage,
    FoliageInventory,
    Occasion,
    Style,
    Wrapping,
    WrappingInventory,
)
from app.services.llm_provider import InvalidLLMOutputError, LLMProviderError

COMPLETE = {
    "occasion": "Birthday", "styles": ["Modern"], "colors": ["Red"],
    "size": "SMALL", "budget_max": "100", "preferred_flowers": ["Rose"],
}


class FakeProvider:
    """Record each call and supply one structured answer or failure."""

    def __init__(self):
        self.output = dict(COMPLETE)
        self.error = None
        self.calls = []

    def generate_structured(self, prompt, schema, *, json_schema=None):
        self.calls.append((prompt, schema, json_schema))
        if self.error:
            raise self.error
        return self.output


@pytest.fixture
def catalog(db_session):
    """Seed two florists with different active catalog choices and real stock."""
    db_session.add_all([
        Florist(id=1, name="First"), Florist(id=2, name="Second"),
        Flower(id=1, name="Rose"), Flower(id=2, name="Lily"), Flower(id=3, name="Sunflower"),
        Occasion(id=1, name="Birthday"), Occasion(id=2, name="Wedding"),
        Style(id=1, name="Modern"), Style(id=2, name="Rustic"),
        Color(id=1, name="Red"), Color(id=2, name="Yellow"),
        Foliage(id=1, name="Green"), Wrapping(id=1, name="Paper"),
    ])
    db_session.flush()
    for florist_id, flower_id, attribute_id in [(1, 1, 1), (1, 2, 1), (2, 3, 2)]:
        db_session.add_all([
            FloristFlower(florist_id=florist_id, flower_id=flower_id, price=10, active=True),
            FlowerInventory(florist_id=florist_id, flower_id=flower_id, quantity=30),
            FlowerOccasion(flower_id=flower_id, occasion_id=attribute_id),
            FlowerStyle(flower_id=flower_id, style_id=attribute_id),
            FlowerColor(flower_id=flower_id, color_id=attribute_id),
        ])
    db_session.add_all([
        FloristFoliage(florist_id=1, foliage_id=1, price=2, active=True),
        FloristWrapping(florist_id=1, wrapping_id=1, price=3, active=True),
        FoliageInventory(florist_id=1, foliage_id=1, quantity=30),
        WrappingInventory(florist_id=1, wrapping_id=1, quantity=30),
    ])
    db_session.flush()


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def api(db_session, catalog, provider):
    """Override only DB/provider boundaries; run real routing and application services."""
    def database():
        yield db_session

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_interpretation_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_interpretation_provider, None)


def test_complete_draft_then_real_recommendation_is_two_requests(api, provider, db_session):
    response = api.post("/florists/1/interpretations", json={"text": "  A small bouquet with roses.  "})
    assert response.status_code == 200
    draft = response.json()
    assert draft["requires_review"] is False
    assert draft["readiness"]["status"] == "READY"
    assert draft["text"] == "A small bouquet with roses."
    assert draft["options"]["flowers"] == ["Lily", "Rose"]
    assert draft["field_sources"]["preferred_flowers"]["relation"] == "AGREEMENT"
    evidence = draft["field_sources"]["preferred_flowers"]["evidence"][0]
    assert draft["text"][evidence["start"]:evidence["end"]] == evidence["text"]
    assert len(provider.calls) == 1
    assert provider.calls[0][2]["properties"]["preferred_flowers"]["anyOf"][0]["items"]["enum"] == ["Lily", "Rose"]
    assert db_session.scalar(select(func.count()).select_from(Bouquet)) == 0
    assert db_session.get(FlowerInventory, (1, 1)).quantity == 30
    # A user may confirm or edit this request; the engine still sets quantities/prices.
    recommendation = api.post("/florists/1/recommendations", json=draft["recommendation_request"])
    assert recommendation.status_code == 200
    assert recommendation.json()["total_price"] == "35.00"
    assert recommendation.json()["flowers"][0]["name"] == "Rose"
    assert len(provider.calls) == 1
    assert db_session.scalar(select(func.count()).select_from(Bouquet)) == 0
    assert db_session.get(FlowerInventory, (1, 1)).quantity == 30


def test_conflict_can_be_corrected_by_user_without_reinterpretation(api, provider):
    provider.output = {**COMPLETE, "size": "LARGE"}
    result = api.post("/florists/1/interpretations", json={"text": "A small bouquet with roses."}).json()
    assert result["interpretation"]["size"] is None
    assert result["requires_review"] is True
    assert result["recommendation_request"] is None
    assert result["issues"][0]["code"] == "SCALAR_CONTRADICTION"
    assert result["field_sources"]["size"]["llm_value"] == "LARGE"
    assert result["field_sources"]["size"]["extractor_value"] == "SMALL"
    corrected = {**COMPLETE, "size": "SMALL", "preferred_flowers": ["Lily"]}
    response = api.post("/florists/1/recommendations", json=corrected)
    assert response.status_code == 200
    assert response.json()["flowers"][0]["name"] == "Lily"
    assert len(provider.calls) == 1


def test_incomplete_draft_does_not_invent_missing_preferences(api, provider):
    provider.output = {"occasion": "Birthday"}
    response = api.post("/florists/1/interpretations", json={"text": "Birthday gift"})
    body = response.json()
    assert response.status_code == 200
    assert body["requires_review"] is True
    assert body["readiness"]["missing_fields"] == ["styles", "colors", "size"]
    assert body["interpretation"]["preferred_flowers"] is None
    assert body["recommendation_request"] is None


@pytest.mark.parametrize("payload", [{"text": " "}, {"text": "Hi", "model": "other"}, {}])
def test_invalid_interpretation_inputs_return_422(api, provider, payload):
    assert api.post("/florists/1/interpretations", json=payload).status_code == 422
    assert not provider.calls


def test_missing_florist_returns_404_before_inference(api, provider):
    assert api.post("/florists/999/interpretations", json={"text": "A bouquet"}).status_code == 404
    assert not provider.calls


@pytest.mark.parametrize("error,status", [
    (LLMProviderError("secret infrastructure info"), 503),
    (InvalidLLMOutputError("raw generated content"), 502),
])
def test_provider_failure_is_sanitized_and_not_retried(api, provider, error, status):
    provider.error = error
    response = api.post("/florists/1/interpretations", json={"text": "A small bouquet"})
    assert response.status_code == status
    assert str(error) not in response.text
    assert len(provider.calls) == 1


@pytest.mark.parametrize("override", [
    {"preferred_flowers": ["Sunflower"]}, {"styles": ["Red"]},
    {"budget_max": "-1"}, {"size": "HUGE"},
])
def test_invalid_provider_values_cannot_bypass_canonical_validation(api, provider, override):
    provider.output = {**COMPLETE, **override}
    response = api.post("/florists/1/interpretations", json={"text": "A bouquet"})
    assert response.status_code == 502
    assert len(provider.calls) == 1


def test_catalog_snapshot_is_scoped_to_each_florist(api, provider):
    provider.output = {
        "occasion": "Wedding", "styles": ["Rustic"], "colors": ["Yellow"],
        "size": "SMALL", "preferred_flowers": ["Sunflower"],
    }
    response = api.post("/florists/2/interpretations", json={"text": "A small bouquet with sunflowers"})
    assert response.status_code == 200
    assert response.json()["options"]["flowers"] == ["Sunflower"]
    assert '"Rose"' not in provider.calls[0][0]
    assert response.json()["requires_review"] is False


@pytest.mark.parametrize("override", [
    {"preferred_flowers": ["Sunflower"]}, {"styles": ["Unknown"]},
    {"excluded_flowers": ["Rose"]}, {"budget_max": "0"}, {"budget_max": "-1"},
])
def test_final_user_preferences_are_revalidated(api, override):
    response = api.post("/florists/1/recommendations", json={**COMPLETE, **override})
    assert response.status_code == 422


def test_catalog_and_stock_changes_are_checked_at_recommendation_time(api, db_session):
    draft = api.post("/florists/1/interpretations", json={"text": "A small bouquet with roses"}).json()
    db_session.get(FloristFlower, (1, 1)).active = False
    db_session.flush()
    assert api.post("/florists/1/recommendations", json=draft["recommendation_request"]).status_code == 422
    db_session.get(FloristFlower, (1, 1)).active = True
    db_session.get(FlowerInventory, (1, 1)).quantity = 0
    db_session.get(FlowerInventory, (1, 2)).quantity = 0
    db_session.flush()
    response = api.post("/florists/1/recommendations", json=draft["recommendation_request"])
    assert response.status_code == 422
    assert response.json()["detail"] == "No valid bouquet recommendation could be generated."


def test_manual_recommendation_does_not_depend_on_llm_configuration(api, monkeypatch, provider):
    app.dependency_overrides.pop(get_interpretation_provider)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    response = api.post("/florists/1/interpretations", json={"text": "A bouquet"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Interpretation service is not configured."
    assert api.post("/florists/1/recommendations", json=COMPLETE).status_code == 200
    assert not provider.calls


def test_explicit_empty_style_list_keeps_existing_manual_request_semantics(api, provider):
    assert api.post("/florists/1/recommendations", json={**COMPLETE, "styles": []}).status_code == 200
    assert not provider.calls


def test_catalog_read_failure_is_sanitized_without_calling_provider(api, provider, monkeypatch):
    def unavailable(db, florist_id):
        raise SQLAlchemyError("private database details")

    monkeypatch.setattr("app.services.interpretation_flow.get_interpretation_catalog", unavailable)
    response = api.post("/florists/1/interpretations", json={"text": "A bouquet"})
    assert response.status_code == 503
    assert "private database details" not in response.text
    assert not provider.calls


def test_real_adapter_request_is_pinned_and_constrained_without_network(api, monkeypatch):
    app.dependency_overrides.pop(get_interpretation_provider)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:1.7b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.delenv("OLLAMA_THINK", raising=False)
    calls = []

    def fake_urlopen(request, timeout):
        body = json.loads(request.data)
        calls.append(body)
        return BytesIO(json.dumps({"message": {"content": json.dumps(COMPLETE)}}).encode())

    monkeypatch.setattr("app.services.ollama_provider.urlopen", fake_urlopen)
    response = api.post("/florists/1/interpretations", json={"text": "A small bouquet with roses"})
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["model"] == "qwen3:1.7b"
    assert calls[0]["think"] is False
    assert calls[0]["options"] == {"temperature": 0}
    assert calls[0]["format"]["properties"]["occasion"]["anyOf"][0]["enum"] == ["Birthday"]
    assert calls[0]["messages"][0]["content"].endswith(json.dumps(calls[0]["format"], ensure_ascii=False))


def test_openapi_does_not_expose_gold_annotation_contracts():
    document = json.dumps(app.openapi())
    assert "/florists/{florist_id}/interpretations" in document
    for experimental in ("annotation_version", "unresolved_mentions", "resolved_values", "AnnotationPrediction", '"PARTIAL"'):
        assert experimental not in document
