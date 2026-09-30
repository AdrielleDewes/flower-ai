"""Tests for the Ollama adapter without a running Ollama server."""

import json
from decimal import Decimal
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from app.config import OllamaConfig
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.services.llm_bouquet_request_interpreter import LLMBouquetRequestInterpreter
from app.services.llm_provider import InvalidLLMOutputError, LLMProviderError
from app.services.ollama_provider import OllamaProvider


def make_provider():
    """Build an adapter with explicit local settings for tests."""
    return OllamaProvider(
        OllamaConfig(
            model="installed-test-model",
            base_url="http://localhost:11434/",
            timeout_seconds=12.5,
        )
    )


def ollama_response(content):
    """Represent a nonstreaming Ollama chat response."""
    return BytesIO(json.dumps({"message": {"content": content}}).encode())


def test_ollama_provider_sends_schema_and_returns_valid_data(monkeypatch):
    """Ollama's JSON content becomes data for the provider contract."""
    observed = {}

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        observed["body"] = json.loads(request.data)
        observed["content_type"] = request.get_header("Content-type")
        observed["method"] = request.get_method()
        return ollama_response(
            json.dumps(
                {
                    "occasion": "Birthday",
                    "size": "SMALL",
                    "budget_max": "75.50",
                    "colors": ["Red"],
                }
            )
        )

    monkeypatch.setattr("app.services.ollama_provider.urlopen", fake_urlopen)

    output = make_provider().generate_structured(
        "A small red birthday bouquet under 75.50",
        BouquetInterpretation,
    )

    assert output == {
        "occasion": "Birthday",
        "size": "SMALL",
        "budget_max": Decimal("75.50"),
        "colors": ["Red"],
    }
    assert observed["url"] == "http://localhost:11434/api/chat"
    assert observed["timeout"] == 12.5
    assert observed["method"] == "POST"
    assert observed["content_type"] == "application/json"
    assert observed["body"] == {
        "model": "installed-test-model",
        "messages": [
            {
                "role": "user",
                "content": "A small red birthday bouquet under 75.50",
            }
        ],
        "stream": False,
        "format": BouquetInterpretation.model_json_schema(),
    }


def test_ollama_provider_preserves_unknown_fields_through_interpreter(monkeypatch):
    """The adapter does not invent values when the model omits fields."""
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: ollama_response('{"occasion":"Birthday"}'),
    )

    result = LLMBouquetRequestInterpreter(make_provider()).interpret(
        "Birthday bouquet"
    )

    assert result.occasion == "Birthday"
    assert result.styles is None
    assert result.colors is None
    assert result.size is None
    assert result.budget_max is None
    assert result.preferred_flowers is None
    assert result.excluded_flowers is None


@pytest.mark.parametrize(
    "response_body",
    [
        b"not json",
        b'{}',
        b'{"message":{"content":"not json"}}',
        b'{"message":{"content":"{\\"size\\":\\"HUGE\\"}"}}',
        b'{"message":{"content":"{\\"unknown\\":1}"}}',
    ],
)
def test_ollama_provider_rejects_invalid_responses(monkeypatch, response_body):
    """Invalid envelopes, JSON, and schema values share one output error."""
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: BytesIO(response_body),
    )

    with pytest.raises(InvalidLLMOutputError):
        make_provider().generate_structured("A bouquet", BouquetInterpretation)


@pytest.mark.parametrize(
    "failure, message",
    [
        (URLError("connection refused"), "Could not connect to Ollama"),
        (TimeoutError("timed out"), "Ollama request timed out"),
        (URLError(TimeoutError("timed out")), "Ollama request timed out"),
        (
            HTTPError("http://localhost:11434/api/chat", 404, "not found", None, None),
            "model 'installed-test-model' is unavailable",
        ),
        (
            HTTPError("http://localhost:11434/api/chat", 500, "error", None, None),
            "HTTP status 500",
        ),
    ],
)
def test_ollama_provider_maps_transport_errors(monkeypatch, failure, message):
    """Transport and model failures become provider errors with their cause."""
    def fake_urlopen(request, timeout):
        raise failure

    monkeypatch.setattr("app.services.ollama_provider.urlopen", fake_urlopen)

    with pytest.raises(LLMProviderError, match=message) as error:
        make_provider().generate_structured("A bouquet", BouquetInterpretation)

    assert error.value.__cause__ is failure


def test_ollama_provider_maps_error_envelope(monkeypatch):
    """An Ollama error message is a provider failure even with HTTP 200."""
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: BytesIO(b'{"error":"generation failed"}'),
    )

    with pytest.raises(LLMProviderError, match="failed to generate"):
        make_provider().generate_structured("A bouquet", BouquetInterpretation)


def test_interpreter_preserves_invalid_ollama_output_error(monkeypatch):
    """Malformed Ollama data stays distinct from transport failures."""
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: ollama_response("not json"),
    )

    with pytest.raises(InvalidLLMOutputError):
        LLMBouquetRequestInterpreter(make_provider()).interpret("A bouquet")


def test_ollama_config_reads_environment(monkeypatch):
    """Model, URL, and timeout come from environment settings."""
    monkeypatch.setenv("OLLAMA_MODEL", "local-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "9.5")

    config = OllamaConfig.from_env()

    assert config.model == "local-model"
    assert config.base_url == "http://127.0.0.1:11434"
    assert config.timeout_seconds == 9.5


@pytest.mark.parametrize(
    "settings",
    [
        {"model": "", "base_url": "http://localhost:11434"},
        {"model": "local", "base_url": "not-a-url"},
        {"model": "local", "base_url": "http://localhost:11434", "timeout_seconds": 0},
    ],
)
def test_ollama_config_rejects_unusable_settings(settings):
    """The adapter must not run with missing or invalid connection settings."""
    with pytest.raises(ValueError):
        OllamaConfig(**settings)
