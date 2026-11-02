import pytest
from fastapi import HTTPException

from app.dependencies import get_florist, get_interpretation_provider
from app.models.florist import Florist


def test_get_florist_returns_requested_florist(db_session):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()

    result = get_florist(florist.id, db_session)

    assert result is florist


def test_get_florist_raises_404_for_unknown_id(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_florist(99999, db_session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Florist not found."


def test_interpretation_provider_is_request_local_and_explicitly_no_thinking(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:1.7b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.delenv("OLLAMA_THINK", raising=False)
    first = get_interpretation_provider()
    second = get_interpretation_provider()
    assert first is not second
    assert first.config.model == "qwen3:1.7b"
    assert first.config.think is False
    first.last_inference_metrics["eval_count"] = 20
    assert second.last_inference_metrics["eval_count"] is None


@pytest.mark.parametrize("model,think", [("gemma3:1b", "false"), ("qwen3:1.7b", "true")])
def test_poc_provider_rejects_incompatible_model_settings(monkeypatch, model, think):
    monkeypatch.setenv("OLLAMA_MODEL", model)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_THINK", think)
    with pytest.raises(HTTPException) as exc:
        get_interpretation_provider()
    assert exc.value.status_code == 503
    assert exc.value.detail == "Interpretation service is not configured."
