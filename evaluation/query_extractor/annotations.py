"""Read-only dataset projection and reviewed, hash-bound auxiliary annotations."""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .annotation_v2 import validate_field_v2
from .contracts import FIELDS, ExtractionState, FlowerVocabulary


def field_values(field: str, raw: Any) -> tuple[str | Decimal, ...]:
    """Project only the four supported labels, without canonical Pydantic schemas."""
    if raw is None:
        return ()
    if field == "budget_max":
        try:
            value = Decimal(str(raw))
        except InvalidOperation as exc:
            raise ValueError("Invalid budget label.") from exc
        if not value.is_finite() or value <= 0:
            raise ValueError("Budget label must be finite and positive.")
        return (value,)
    if field == "size":
        if raw not in {"SMALL", "MEDIUM", "LARGE"}:
            raise ValueError("Invalid size label.")
        return (raw,)
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ValueError("Flower labels must be lists of canonical names.")
    return tuple(raw)


@dataclass(frozen=True)
class AnnotatedCase:
    """An existing query with reviewed language, states and support spans."""

    id: str
    query: str
    language: str
    expected: dict[str, tuple[str | Decimal, ...]]
    annotations: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class PreparedEvaluation:
    """Validated inputs only; loading this object performs no extraction."""

    catalog: FlowerVocabulary
    cases: tuple[AnnotatedCase, ...]
    dataset_sha256: str
    dataset_version: int
    annotation_version: int = 1


def _read_dataset(path: Path) -> tuple[dict[str, Any], str]:
    """Read the original dataset without rewriting or importing application code."""
    content = path.read_bytes()
    dataset = json.loads(content)
    if not isinstance(dataset, dict) or dataset.get("version") not in {1, 2}:
        raise ValueError("Expected an existing version 1 or 2 dataset.")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Dataset must contain cases.")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Dataset case IDs must be unique.")
    return dataset, hashlib.sha256(content).hexdigest()


def annotation_template(path: Path, *, annotation_version: int = 1) -> dict[str, Any]:
    """Create unreviewed shells; this is annotation preparation, not evaluation."""
    dataset, digest = _read_dataset(path)
    if type(annotation_version) is not int or annotation_version not in {1, 2}:
        raise ValueError("Unsupported annotation version.")
    return {
        "annotation_version": annotation_version,
        "dataset_sha256": digest,
        "cases": [
            {
                "id": case["id"], "language": None, "reviewed": False,
                "fields": {
                    field: (
                        {"state": None, "evidence": []} if annotation_version == 1 else
                        {"state": None, "resolved_values": [], "unresolved_mentions": []}
                    )
                    for field in FIELDS
                },
            }
            for case in dataset["cases"]
        ],
    }


def _validate_annotation(
    query: str, field: str, annotation: dict[str, Any], expected: tuple,
) -> None:
    """Check consistency and spans; semantic correctness still requires review."""
    state = ExtractionState(annotation["state"])
    if bool(expected) != (state is ExtractionState.RESOLVED):
        raise ValueError(f"Annotation state contradicts dataset label for {field}.")
    evidence = annotation["evidence"]
    if not isinstance(evidence, list):
        raise ValueError("Evidence must be a list.")
    if state is ExtractionState.ABSENT and evidence:
        raise ValueError("Absent fields must not contain supporting evidence.")
    if state is not ExtractionState.ABSENT and not evidence:
        raise ValueError("Resolved or pending fields require reviewed evidence.")
    supported = set()
    for span in evidence:
        start, end = span["start"], span["end"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(query):
            raise ValueError("Evidence offsets must be valid original-query indices.")
        if query[start:end] != span["text"]:
            raise ValueError("Evidence text does not match the original query.")
        if state is ExtractionState.RESOLVED:
            raw = span["value"] if field in {"size", "budget_max"} else [span["value"]]
            supported.update(field_values(field, raw))
    if state is ExtractionState.RESOLVED and supported != set(expected):
        raise ValueError("Reviewed evidence must cover exactly the expected values.")


def load_annotated_dataset(dataset_path: Path, annotation_path: Path) -> PreparedEvaluation:
    """Require complete, reviewed annotations bound to the original dataset bytes."""
    dataset, digest = _read_dataset(dataset_path)
    annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
    version = annotations.get("annotation_version")
    if type(version) is not int or version not in {1, 2}:
        raise ValueError("Unsupported annotation version.")
    if annotations.get("dataset_sha256") != digest:
        raise ValueError("Annotation dataset hash mismatch.")
    entries = annotations["cases"]
    indexed = {entry["id"]: entry for entry in entries}
    if len(indexed) != len(entries) or set(indexed) != {case["id"] for case in dataset["cases"]}:
        raise ValueError("Annotations must cover every dataset ID exactly once.")
    catalog = FlowerVocabulary(dataset["catalog"]["flowers"])
    prepared = []
    for case in dataset["cases"]:
        entry = indexed[case["id"]]
        if entry.get("reviewed") is not True or entry.get("language") not in {"pt", "en"}:
            raise ValueError("Every case needs explicit review and language pt/en.")
        if set(entry["fields"]) != set(FIELDS):
            raise ValueError("Annotations must specify all four fields.")
        query = case["input"]
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Dataset queries must be nonempty strings.")
        expected = {field: field_values(field, case["expected"][field]) for field in FIELDS}
        for field in ("preferred_flowers", "excluded_flowers"):
            if not set(expected[field]) <= set(catalog.flowers):
                raise ValueError("Expected flower is outside the dataset catalog.")
        for field in FIELDS:
            if version == 1:
                _validate_annotation(query, field, entry["fields"][field], expected[field])
            else:
                validate_field_v2(query, field, entry["fields"][field], catalog, expected[field])
        prepared.append(AnnotatedCase(case["id"], query, entry["language"], expected, entry["fields"]))
    return PreparedEvaluation(catalog, tuple(prepared), digest, dataset["version"], version)
