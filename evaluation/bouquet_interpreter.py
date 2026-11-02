"""Evaluate a bouquet interpreter against a fixed, catalog-grounded dataset."""

import argparse
import json
import os
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.config import OllamaConfig
from app.schemas.bouquet_interpretation import (
    BouquetInterpretation,
    BouquetRequestReadinessStatus,
)
from app.schemas.catalog import InterpretationCatalog
from app.services.bouquet_interpretation import assess_bouquet_interpretation
from app.services.bouquet_request_interpreter import BouquetRequestInterpreter
from app.services.catalog_output_schema import CATALOG_CONSTRAINT_VERSION
from app.services.llm_bouquet_request_interpreter import (
    LLMBouquetRequestInterpreter,
    validate_catalog_values,
)
from app.services.llm_provider import LLMProviderError
from app.services.ollama_provider import OllamaProvider

DATASET_PATHS = {
    version: Path(__file__).parent / "data" / f"bouquet_requests_v{version}.json"
    for version in (1, 2)
}
DEFAULT_DATASET = DATASET_PATHS[1]
INTERPRETATION_FIELDS = tuple(BouquetInterpretation.model_fields)


class EvaluationCase(BaseModel):
    """One customer utterance and its complete expected interpretation."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    input: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    expected: BouquetInterpretation
    expected_status: BouquetRequestReadinessStatus | None = None

    @model_validator(mode="before")
    @classmethod
    def require_all_expected_fields(cls, value: Any) -> Any:
        """Keep nulls explicit so dataset omissions cannot become accidental labels."""
        if isinstance(value, dict) and isinstance(value.get("expected"), dict):
            expected_fields = set(value["expected"])
            if expected_fields != set(INTERPRETATION_FIELDS):
                raise ValueError("Expected interpretation must specify every field.")
        return value


class EvaluationDataset(BaseModel):
    """Versioned cases and the fixed vocabulary supplied to the interpreter."""

    model_config = ConfigDict(extra="forbid")

    version: int
    catalog: InterpretationCatalog
    cases: list[EvaluationCase]

    @model_validator(mode="after")
    def validate_cases(self) -> "EvaluationDataset":
        """Ensure each expected answer uses the evaluation catalog."""
        if self.version not in DATASET_PATHS:
            raise ValueError("Unsupported evaluation dataset version.")
        if not self.cases:
            raise ValueError("Evaluation dataset must contain cases.")
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation case IDs must be unique.")
        inputs = [case.input.casefold() for case in self.cases]
        if len(inputs) != len(set(inputs)):
            raise ValueError("Evaluation case inputs must be unique.")
        for case in self.cases:
            try:
                validate_catalog_values(case.expected, self.catalog)
            except ValueError as exc:
                raise ValueError(f"Invalid catalog value in case {case.id}.") from exc
            if self.version >= 2 and case.expected_status is None:
                raise ValueError(f"Expected readiness status is required in case {case.id}.")
            derived_status = assess_bouquet_interpretation(case.expected).status
            if case.expected_status is not None and case.expected_status != derived_status:
                raise ValueError(f"Inconsistent expected readiness status in case {case.id}.")
        return self


def load_dataset(path: Path = DEFAULT_DATASET) -> EvaluationDataset:
    """Load the versioned JSON dataset without connecting to a model or database."""
    return EvaluationDataset.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_dataset(
    interpreter: BouquetRequestInterpreter,
    dataset: EvaluationDataset,
    clock: Callable[[], float] = perf_counter,
) -> dict[str, Any]:
    """Compare every case and report failures without aborting later cases."""
    field_correct = dict.fromkeys(INTERPRETATION_FIELDS, 0)
    status_names = tuple(status.value for status in BouquetRequestReadinessStatus)
    readiness = {
        status: {"expected": 0, "actual": 0, "correct": 0}
        for status in status_names
    }
    exact_matches = 0
    invented_values = 0
    evaluated_absent_fields = 0
    failed_cases = 0
    latencies = []
    case_results = []
    inference_metric_totals: dict[str, int] = defaultdict(int)
    inference_metric_counts: dict[str, int] = defaultdict(int)
    inference_responses = 0

    def capture_metrics() -> dict[str, int | float | None] | None:
        """Copy the provider's response metrics before its next request."""
        nonlocal inference_responses
        provider = getattr(interpreter, "provider", None)
        metrics = getattr(provider, "last_inference_metrics", None)
        if not isinstance(metrics, dict):
            return None

        snapshot = dict(metrics)
        metric_names = (
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
            "prompt_eval_count",
            "eval_count",
        )
        if any(isinstance(snapshot.get(name), int) for name in metric_names):
            inference_responses += 1
        for name in metric_names:
            value = snapshot.get(name)
            if isinstance(value, int) and not isinstance(value, bool):
                inference_metric_totals[name] += value
                inference_metric_counts[name] += 1
        return snapshot

    for case in dataset.cases:
        expected = case.expected.model_dump(mode="json")
        expected_status = (
            case.expected_status or assess_bouquet_interpretation(case.expected).status
        ).value
        readiness[expected_status]["expected"] += 1
        started = clock()
        try:
            actual_interpretation = interpreter.interpret(case.input)
            if not isinstance(actual_interpretation, BouquetInterpretation):
                actual_interpretation = BouquetInterpretation.model_validate(
                    actual_interpretation
                )
            elapsed = clock() - started
            ollama_metrics = capture_metrics()
        except (LLMProviderError, ValueError) as exc:
            elapsed = clock() - started
            ollama_metrics = capture_metrics()
            failed_cases += 1
            latencies.append(elapsed)
            case_results.append({
                "id": case.id,
                "expected": expected,
                "actual": None,
                "expected_status": expected_status,
                "actual_status": None,
                "latency_seconds": elapsed,
                "ollama_metrics": ollama_metrics,
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        latencies.append(elapsed)
        actual = actual_interpretation.model_dump(mode="json")
        field_matches = {}
        for field in INTERPRETATION_FIELDS:
            matches = expected[field] == actual[field]
            field_matches[field] = matches
            field_correct[field] += matches
            if expected[field] is None:
                evaluated_absent_fields += 1
                invented_values += actual[field] is not None

        exact_match = all(field_matches.values())
        exact_matches += exact_match
        actual_status = assess_bouquet_interpretation(actual_interpretation).status.value
        readiness[actual_status]["actual"] += 1
        readiness[expected_status]["correct"] += actual_status == expected_status
        case_results.append({
            "id": case.id,
            "expected": expected,
            "actual": actual,
            "field_matches": field_matches,
            "exact_match": exact_match,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "latency_seconds": elapsed,
            "ollama_metrics": ollama_metrics,
            "error": None,
        })

    total = len(dataset.cases)
    correct_statuses = sum(counts["correct"] for counts in readiness.values())
    eval_duration = inference_metric_totals.get("eval_duration", 0)
    eval_count = inference_metric_totals.get("eval_count", 0)
    return {
        "dataset_version": dataset.version,
        "cases_total": total,
        "cases_completed": total - failed_cases,
        "cases_failed": failed_cases,
        "exact_match": {
            "correct": exact_matches,
            "total": total,
            "rate": exact_matches / total,
        },
        "field_accuracy": {
            field: {
                "correct": count,
                "total": total,
                "rate": count / total,
            }
            for field, count in field_correct.items()
        },
        "invented_values": {
            "count": invented_values,
            "evaluated_absent_fields": evaluated_absent_fields,
            "rate": (
                invented_values / evaluated_absent_fields
                if evaluated_absent_fields else None
            ),
        },
        "mean_latency_seconds": fmean(latencies),
        "total_latency_seconds": sum(latencies),
        "ollama_inference_metrics": {
            "responses_with_metrics": inference_responses,
            "totals": {
                name: inference_metric_totals.get(name)
                for name in (
                    "total_duration",
                    "load_duration",
                    "prompt_eval_duration",
                    "eval_duration",
                    "prompt_eval_count",
                    "eval_count",
                )
            },
            "responses_by_metric": {
                name: inference_metric_counts.get(name, 0)
                for name in (
                    "total_duration",
                    "load_duration",
                    "prompt_eval_duration",
                    "eval_duration",
                    "prompt_eval_count",
                    "eval_count",
                )
            },
            "eval_tokens_per_second": (
                eval_count * 1_000_000_000 / eval_duration
                if eval_duration else None
            ),
        },
        "readiness": {
            "correct": correct_statuses,
            "total": total,
            "rate": correct_statuses / total,
            "by_status": readiness,
        },
        "cases": case_results,
    }


def main() -> int:
    """Run the fixed dataset manually with a selected local Ollama model."""
    parser = argparse.ArgumentParser(description=__doc__)
    dataset_selection = parser.add_mutually_exclusive_group()
    dataset_selection.add_argument("--dataset", type=Path)
    dataset_selection.add_argument(
        "--dataset-version", type=int, choices=tuple(DATASET_PATHS),
        help="Select a bundled dataset version (default: 1)",
    )
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", ""))
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument(
        "--think",
        action=argparse.BooleanOptionalAction,
        default=OllamaConfig.parse_optional_bool(os.getenv("OLLAMA_THINK")),
        help="Enable or disable thinking; omit to use the model default",
    )
    parser.add_argument("--output", type=Path, help="Write the JSON report to this file")
    parser.add_argument(
        "--catalog-constrained-output", action="store_true",
        help="Experimentally restrict generation to catalog values (default: disabled)",
    )
    args = parser.parse_args()
    dataset_path = args.dataset or DATASET_PATHS[args.dataset_version or 1]

    try:
        timeout = (
            args.timeout_seconds
            if args.timeout_seconds is not None
            else float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
        )
        config = OllamaConfig(
            model=args.model, base_url=args.base_url, timeout_seconds=timeout,
            think=args.think,
        )
        dataset = load_dataset(dataset_path)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Invalid evaluation configuration or dataset: {exc}\n")

    provider = OllamaProvider(config)
    if args.catalog_constrained_output:
        interpreter = LLMBouquetRequestInterpreter(
            provider, dataset.catalog, catalog_constraints=True,
        )
    else:
        interpreter = LLMBouquetRequestInterpreter(provider, dataset.catalog)
    report = evaluate_dataset(interpreter, dataset)
    report["configuration"] = {
        "model": config.model,
        "base_url": config.base_url,
        "timeout_seconds": config.timeout_seconds,
        "think": config.think,
        "dataset": str(dataset_path),
        "catalog_constrained_output": args.catalog_constrained_output,
        "catalog_constraint_version": (
            CATALOG_CONSTRAINT_VERSION if args.catalog_constrained_output else None
        ),
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 1 if report["cases_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
