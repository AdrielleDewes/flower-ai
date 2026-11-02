"""Ollama adapter for the structured LLM provider contract."""

import json
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from app.config import OllamaConfig
from app.services.llm_provider import InvalidLLMOutputError, LLMProviderError


class OllamaProvider:
    """Request and validate structured responses from a local Ollama server."""

    def __init__(self, config: OllamaConfig) -> None:
        """Use explicit settings without connecting to Ollama yet."""
        self.config = config
        self.last_total_duration_ns: int | None = None
        self.last_inference_metrics = self._empty_inference_metrics()

    @staticmethod
    def _empty_inference_metrics() -> dict[str, int | float | None]:
        """Represent missing Ollama response metrics explicitly as null."""
        return {
            "total_duration": None,
            "load_duration": None,
            "prompt_eval_duration": None,
            "eval_duration": None,
            "prompt_eval_count": None,
            "eval_count": None,
            "eval_tokens_per_second": None,
        }

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert Ollama's JSON message content to validated structured data."""
        self.last_total_duration_ns = None
        self.last_inference_metrics = self._empty_inference_metrics()
        output_schema = schema.model_json_schema() if json_schema is None else json_schema
        grounded_prompt = (
            f"{prompt}\n\nOutput JSON schema:\n"
            f"{json.dumps(output_schema, ensure_ascii=False)}"
        )
        request_body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": grounded_prompt}],
            "stream": False,
            "format": output_schema,
            "options": {"temperature": 0},
        }
        if self.config.think is not None:
            request_body["think"] = self.config.think

        request = Request(
            url=f"{self.config.base_url.rstrip('/')}/api/chat",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_body = response.read()
        except HTTPError as exc:
            if exc.code == 404:
                raise LLMProviderError(
                    f"Ollama model '{self.config.model}' is unavailable."
                ) from exc
            raise LLMProviderError(
                f"Ollama request failed with HTTP status {exc.code}."
            ) from exc
        except TimeoutError as exc:
            raise LLMProviderError("Ollama request timed out.") from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise LLMProviderError("Ollama request timed out.") from exc
            raise LLMProviderError("Could not connect to Ollama.") from exc
        except OSError as exc:
            raise LLMProviderError("Could not connect to Ollama.") from exc

        try:
            envelope = json.loads(response_body)
            if not isinstance(envelope, dict):
                raise TypeError("Ollama response must be an object.")
            self._capture_inference_metrics(envelope)
            if "error" in envelope:
                raise LLMProviderError("Ollama failed to generate a response.")

            message = envelope.get("message")
            if not isinstance(message, dict):
                raise TypeError("Ollama response has no message.")
            content = message.get("content")
            if not isinstance(content, str):
                raise TypeError("Ollama message has no content.")
            output = json.loads(content, parse_float=Decimal)
            validated = schema.model_validate(output)
        except (UnicodeDecodeError, TypeError, ValueError, ValidationError) as exc:
            raise InvalidLLMOutputError(
                "Ollama returned an invalid structured response."
            ) from exc

        return validated.model_dump(exclude_unset=True)

    def _capture_inference_metrics(self, envelope: dict[str, Any]) -> None:
        """Retain response metrics for evaluation without affecting validation."""
        metric_names = (
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
            "prompt_eval_count",
            "eval_count",
        )
        for name in metric_names:
            value = envelope.get(name)
            if type(value) is int and value >= 0:
                self.last_inference_metrics[name] = value

        total_duration = self.last_inference_metrics["total_duration"]
        if isinstance(total_duration, int):
            self.last_total_duration_ns = total_duration

        eval_count = self.last_inference_metrics["eval_count"]
        eval_duration = self.last_inference_metrics["eval_duration"]
        if isinstance(eval_count, int) and isinstance(eval_duration, int) and eval_duration:
            self.last_inference_metrics["eval_tokens_per_second"] = (
                eval_count * 1_000_000_000 / eval_duration
            )
