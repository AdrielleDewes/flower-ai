"""Run one real bouquet interpretation against the configured local Ollama."""

import argparse
import json
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.config import OllamaConfig
from app.database import SessionLocal
from app.schemas.bouquet_interpretation import BouquetInterpretationInput
from app.services.bouquet_interpretation import assess_bouquet_interpretation
from app.services.catalog import get_interpretation_catalog
from app.services.llm_bouquet_request_interpreter import LLMBouquetRequestInterpreter
from app.services.llm_provider import InvalidLLMOutputError, LLMProviderError
from app.services.ollama_provider import OllamaProvider


def main() -> int:
    """Print the validated interpretation, readiness, and server duration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="Customer bouquet request")
    parser.add_argument("--florist-id", type=int, required=True)
    args = parser.parse_args()

    provider: OllamaProvider | None = None
    try:
        request = BouquetInterpretationInput(text=args.text)
        provider = OllamaProvider(OllamaConfig.from_env())
        with SessionLocal() as db:
            catalog = get_interpretation_catalog(db, args.florist_id)
        interpretation = LLMBouquetRequestInterpreter(provider, catalog).interpret(
            request.text
        )
        readiness = assess_bouquet_interpretation(interpretation)
    except SQLAlchemyError:
        print("Could not read the local catalog database.", file=sys.stderr)
        return 1
    except (ValueError, InvalidLLMOutputError, LLMProviderError) as exc:
        print(f"Interpretation failed: {exc}", file=sys.stderr)
        if provider is not None:
            print(
                f"Ollama total_duration (ns): {provider.last_total_duration_ns}",
                file=sys.stderr,
            )
        return 1

    duration = provider.last_total_duration_ns
    print(json.dumps({
        "model": provider.config.model,
        "interpretation": interpretation.model_dump(mode="json"),
        **readiness.model_dump(mode="json"),
        "ollama_total_duration_ns": duration,
        "ollama_total_duration_seconds": (
            duration / 1_000_000_000 if duration is not None else None
        ),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
