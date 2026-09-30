"""Environment based configuration for optional local integrations."""

import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class OllamaConfig:
    """Connection settings for a locally hosted Ollama model."""

    model: str
    base_url: str
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        """Reject missing model names and unusable connection settings."""
        if not self.model.strip():
            raise ValueError("OLLAMA_MODEL must be set.")

        parsed_url = urlsplit(self.base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("OLLAMA_BASE_URL must be an HTTP URL.")
        if parsed_url.query or parsed_url.fragment:
            raise ValueError("OLLAMA_BASE_URL must not include a query or fragment.")

        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero.")

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Read Ollama settings from environment variables when needed."""
        timeout = os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")
        try:
            timeout_seconds = float(timeout)
        except ValueError as exc:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be a number.") from exc

        return cls(
            model=os.getenv("OLLAMA_MODEL", ""),
            base_url=os.getenv("OLLAMA_BASE_URL", ""),
            timeout_seconds=timeout_seconds,
        )
