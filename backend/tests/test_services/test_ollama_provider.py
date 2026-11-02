"""Tests for the Ollama adapter without a running Ollama server."""

import json
from decimal import Decimal
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from app.config import OllamaConfig
from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog
from app.services.catalog_output_schema import build_catalog_output_schema
from app.services.llm_bouquet_request_interpreter import LLMBouquetRequestInterpreter
from app.services.llm_provider import InvalidLLMOutputError, LLMProviderError
from app.services.ollama_provider import OllamaProvider

CATALOG = InterpretationCatalog(
    occasions=["Birthday"], styles=["Romantic"], colors=["Red"],
    flowers=["Rose", "Lily"],
)


@pytest.mark.parametrize("content,valid", [
    ('{"preferred_flowers": ["Rose"], "colors": null}', True),
    ('{"colors": ["Purple"]}', False),
    ('{"size": "HUGE"}', False),
])
def test_constrained_inference_sends_schema_and_keeps_metrics(monkeypatch, content, valid):
    """The same schema grounds and constrains output; tokens survive rejection."""
    observed = {}
    metrics = {"prompt_eval_count": 1234, "eval_count": 60, "eval_duration": 3_000_000_000}

    def fake_urlopen(request, timeout):
        observed.update(json.loads(request.data))
        return BytesIO(json.dumps({"message": {"content": content}, **metrics}).encode())

    monkeypatch.setattr("app.services.ollama_provider.urlopen", fake_urlopen)
    provider = make_provider(think=False)
    interpreter = LLMBouquetRequestInterpreter(provider, CATALOG, catalog_constraints=True)
    if valid:
        assert interpreter.interpret("Roses please").preferred_flowers == ["Rose"]
    else:
        with pytest.raises(InvalidLLMOutputError):
            interpreter.interpret("Roses please")
    schema = build_catalog_output_schema(CATALOG)
    assert observed["format"] == schema
    assert observed["messages"][0]["content"].endswith(
        "Output JSON schema:\n" + json.dumps(schema, ensure_ascii=False)
    )
    assert observed["think"] is False
    assert observed["options"] == {"temperature": 0}
    assert provider.last_inference_metrics["prompt_eval_count"] == 1234
    assert provider.last_inference_metrics["eval_count"] == 60
    assert provider.last_inference_metrics["eval_tokens_per_second"] == 20


def test_constrained_http_error_has_no_unconstrained_retry(monkeypatch):
    """An unsupported schema fails visibly without another provider request."""
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, 400, "Bad schema", None, None)

    monkeypatch.setattr("app.services.ollama_provider.urlopen", fake_urlopen)
    with pytest.raises(LLMProviderError, match="400"):
        LLMBouquetRequestInterpreter(make_provider(), CATALOG, catalog_constraints=True).interpret("Bouquet")
    assert len(calls) == 1

def make_provider(think=None):
    """Build an adapter with explicit local settings for tests."""
    return OllamaProvider(
        OllamaConfig(
            model="installed-test-model",
            base_url="http://localhost:11434/",
            timeout_seconds=12.5,
            think=think,
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
                "content": (
                    "A small red birthday bouquet under 75.50\n\nOutput JSON schema:\n"
                    + json.dumps(BouquetInterpretation.model_json_schema(), ensure_ascii=False)
                ),
            }
        ],
        "stream": False,
        "format": BouquetInterpretation.model_json_schema(),
        "options": {"temperature": 0},
    }


def test_ollama_provider_sends_explicit_think_false(monkeypatch):
    """The thinking option is sent only when the caller configures it."""
    observed = {}

    def fake_urlopen(request, timeout):
        observed["body"] = json.loads(request.data)
        return ollama_response("{}")

    monkeypatch.setattr("app.services.ollama_provider.urlopen", fake_urlopen)
    provider = make_provider(think=False)
    provider.generate_structured("A bouquet", BouquetInterpretation)

    assert observed["body"]["think"] is False


def test_ollama_provider_captures_inference_metrics_and_generation_rate(monkeypatch):
    """Server telemetry is retained separately from structured interpretation."""
    metrics = {
        "total_duration": 900,
        "load_duration": 100,
        "prompt_eval_duration": 200,
        "eval_duration": 500,
        "prompt_eval_count": 20,
        "eval_count": 4,
    }
    response = {"message": {"content": "{}"}, **metrics}
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: BytesIO(json.dumps(response).encode()),
    )
    provider = make_provider()

    result = provider.generate_structured("A bouquet", BouquetInterpretation)

    assert result == {}
    assert provider.last_inference_metrics == {
        **metrics,
        "eval_tokens_per_second": 8_000_000,
    }
    assert provider.last_total_duration_ns == 900


def test_inference_metrics_survive_invalid_structured_content(monkeypatch):
    """Response timing remains observable when output validation rejects content."""
    response = {
        "message": {"content": "not-json"},
        "total_duration": 42,
        "eval_duration": 21,
        "eval_count": 3,
    }
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: BytesIO(json.dumps(response).encode()),
    )
    provider = make_provider()

    with pytest.raises(InvalidLLMOutputError):
        provider.generate_structured("A bouquet", BouquetInterpretation)

    assert provider.last_inference_metrics["total_duration"] == 42
    assert provider.last_inference_metrics["eval_tokens_per_second"] == pytest.approx(
        3 / 21 * 1e9
    )


def test_ollama_provider_preserves_unknown_fields_through_interpreter(monkeypatch):
    """The adapter does not invent values when the model omits fields."""
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: ollama_response('{"occasion":"Birthday"}'),
    )

    result = LLMBouquetRequestInterpreter(make_provider(), CATALOG).interpret(
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


@pytest.mark.parametrize("duration", [1234567890, 0, None, -1, "123", True])
def test_ollama_duration_is_optional_and_reset_between_calls(monkeypatch, duration):
    """Keep valid server timing without leaking it into subsequent calls."""
    responses = iter([
        BytesIO(json.dumps({
            "message": {"content": "{}"},
            "total_duration": duration,
        }).encode()),
        ollama_response("{}"),
    ])
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: next(responses),
    )
    provider = make_provider()
    assert provider.generate_structured("A bouquet", BouquetInterpretation) == {}
    expected = duration if type(duration) is int and duration >= 0 else None
    assert provider.last_total_duration_ns == expected
    assert provider.last_inference_metrics["total_duration"] == expected

    provider.generate_structured("Another bouquet", BouquetInterpretation)
    assert provider.last_total_duration_ns is None
    assert provider.last_inference_metrics["total_duration"] is None


def test_interpreter_preserves_invalid_ollama_output_error(monkeypatch):
    """Malformed Ollama data stays distinct from transport failures."""
    monkeypatch.setattr(
        "app.services.ollama_provider.urlopen",
        lambda request, timeout: ollama_response("not json"),
    )

    with pytest.raises(InvalidLLMOutputError):
        LLMBouquetRequestInterpreter(make_provider(), CATALOG).interpret("A bouquet")


def test_ollama_config_reads_environment(monkeypatch):
    """Model, URL, and timeout come from environment settings."""
    monkeypatch.setenv("OLLAMA_MODEL", "local-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "9.5")
    monkeypatch.setenv("OLLAMA_THINK", "false")

    config = OllamaConfig.from_env()

    assert config.model == "local-model"
    assert config.base_url == "http://127.0.0.1:11434"
    assert config.timeout_seconds == 9.5
    assert config.think is False


@pytest.mark.parametrize("value, expected", [
    (None, None), ("", None), ("true", True), ("false", False),
    ("ON", True), ("off", False),
])
def test_ollama_config_parses_optional_think(value, expected):
    """Unset retains model defaults while explicit booleans remain distinct."""
    assert OllamaConfig.parse_optional_bool(value) is expected


def test_ollama_config_rejects_invalid_think_value():
    """Unrecognized strings cannot silently enable or disable thinking."""
    with pytest.raises(ValueError, match="OLLAMA_THINK"):
        OllamaConfig.parse_optional_bool("sometimes")


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
