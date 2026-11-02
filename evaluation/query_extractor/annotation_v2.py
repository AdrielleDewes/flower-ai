"""Annotation-only v2 contracts; extraction states and rules remain unchanged."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from .contracts import RULES_VERSION, FlowerVocabulary

FLOWER_FIELDS = {"preferred_flowers", "excluded_flowers"}


class AnnotationState(str, Enum):
    """PARTIAL applies to flower annotations, not the legacy extractor contract."""

    ABSENT = "ABSENT"
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


class UnresolvedReason(str, Enum):
    """Separate unavailable catalog mappings from indecision and contradiction."""

    OUT_OF_CATALOG = "OUT_OF_CATALOG"
    UNDECIDED = "UNDECIDED"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"


@dataclass(frozen=True)
class AnnotationPrediction:
    """Optional v2 prediction interface for standalone evaluators and test doubles.

    The current QueryExtractor still returns its original QueryExtraction. This
    interface adds no recognition rules or production integration.
    """

    fields: dict[str, dict[str, Any]]
    rules_version: str = RULES_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize budgets/candidates losslessly in a standalone v2 report."""
        def encode(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()}
            if isinstance(value, list):
                return [encode(item) for item in value]
            return value

        return encode(self.fields)


def _keys(value: Any, required: set[str]) -> None:
    """Reject ignored metadata and missing keys rather than silently dropping them."""
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"Expected exactly these keys: {sorted(required)}.")


def validate_span(query: str, span: dict[str, Any]) -> None:
    """Check original-character offsets, exclusive end, and exact source text."""
    _keys(span, {"start", "end", "text"})
    start, end = span["start"], span["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(query):
        raise ValueError("Evidence offsets must be valid original-query indices.")
    if not isinstance(span["text"], str) or query[start:end] != span["text"]:
        raise ValueError("Evidence text does not match the original query.")


def canonical_value(field: str, value: Any, catalog: FlowerVocabulary) -> str | Decimal:
    """Validate annotation values without the production Pydantic schemas."""
    if value is None or isinstance(value, bool):
        raise ValueError("Canonical values cannot be null or boolean.")
    if field in FLOWER_FIELDS:
        if not isinstance(value, str) or value not in catalog.flowers:
            raise ValueError("Flower value is outside the active catalog.")
        return value
    if field == "size":
        if not isinstance(value, str) or value not in {"SMALL", "MEDIUM", "LARGE"}:
            raise ValueError("Invalid size value.")
        return value
    if field != "budget_max":
        raise ValueError("Unsupported annotation field.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid budget value.") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Budget value must be finite and positive.")
    return amount


def _evidence(query: str, evidence: Any) -> None:
    """Require support context; overlapping spans in coordinated lists are valid."""
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Every value or pending mention requires evidence.")
    for span in evidence:
        validate_span(query, span)


def validate_field_v2(
    query: str, field: str, annotation: dict[str, Any], catalog: FlowerVocabulary,
    expected: tuple[str | Decimal, ...] | None = None,
) -> None:
    """Validate v2 shape and invariants; OUT_OF_CATALOG still needs human review.

    expected=None validates a prediction's structure without comparing to gold.
    An empty tuple validates that a gold field has no resolved canonical values.
    """
    _keys(annotation, {"state", "resolved_values", "unresolved_mentions"})
    state = AnnotationState(annotation["state"])
    resolved, unresolved = annotation["resolved_values"], annotation["unresolved_mentions"]
    if not isinstance(resolved, list) or not isinstance(unresolved, list):
        raise ValueError("Resolved values and unresolved mentions must be lists.")
    values = []
    for item in resolved:
        _keys(item, {"value", "evidence"})
        values.append(canonical_value(field, item["value"], catalog))
        _evidence(query, item["evidence"])
    if len(values) != len(set(values)):
        raise ValueError("Resolved values must be unique; group their evidence.")
    if field not in FLOWER_FIELDS and len(values) > 1:
        raise ValueError("Scalar fields cannot contain multiple resolved values.")
    if expected is not None and tuple(values) != expected:
        raise ValueError("Resolved values must match dataset labels in original order.")
    positions = set()
    reasons = set()
    for item in unresolved:
        _keys(item, {"reason", "mention", "candidates", "evidence"})
        reason = UnresolvedReason(item["reason"])
        reasons.add(reason)
        validate_span(query, item["mention"])
        position = (item["mention"]["start"], item["mention"]["end"])
        if position in positions:
            raise ValueError("Pending mentions must have unique source positions per field.")
        positions.add(position)
        _evidence(query, item["evidence"])
        if any(not e["start"] <= position[0] < position[1] <= e["end"] for e in item["evidence"]):
            raise ValueError("Each support span must contain its pending mention.")
        if not isinstance(item["candidates"], list):
            raise ValueError("Pending candidates must be a list.")
        candidates = [canonical_value(field, value, catalog) for value in item["candidates"]]
        if len(candidates) != len(set(candidates)):
            raise ValueError("Pending candidates must be unique.")
        if reason is UnresolvedReason.OUT_OF_CATALOG:
            if field not in FLOWER_FIELDS or candidates:
                raise ValueError("OUT_OF_CATALOG is a flower mention without canonical candidates.")
            if item["mention"]["text"].casefold() in {name.casefold() for name in catalog.flowers}:
                raise ValueError("An exact canonical name cannot be OUT_OF_CATALOG.")
    conflict = UnresolvedReason.CONFLICTING_INFORMATION in reasons
    if conflict and len(unresolved) < 2:
        alternatives = {value for item in unresolved for value in item["candidates"]}
        if len(alternatives) < 2:
            raise ValueError("Conflict needs multiple mentions or incompatible candidates.")
    valid = {
        AnnotationState.ABSENT: not resolved and not unresolved,
        AnnotationState.RESOLVED: bool(resolved) and not unresolved,
        AnnotationState.PARTIAL: field in FLOWER_FIELDS and bool(resolved) and bool(unresolved) and not conflict,
        AnnotationState.AMBIGUOUS: not resolved and bool(unresolved) and not conflict,
        AnnotationState.CONFLICT: not resolved and bool(unresolved) and conflict,
    }
    if not valid[state]:
        raise ValueError("Annotation state is inconsistent with resolved/pending content.")
