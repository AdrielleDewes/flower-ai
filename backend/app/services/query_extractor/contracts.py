"""Independent contracts for values, abstentions and original-query evidence."""

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

FIELDS = ("size", "budget_max", "preferred_flowers", "excluded_flowers")
RULES_VERSION = "query-extractor-v1"


class ExtractionState(str, Enum):
    """Distinguish unknown information from unresolved mentions."""

    ABSENT = "ABSENT"
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class FlowerVocabulary:
    """Snapshot of canonical flower names, independent of application schemas."""

    flowers: tuple[str, ...]

    def __post_init__(self) -> None:
        """Snapshot mutable inputs and reject unusable canonical names."""
        if isinstance(self.flowers, str):
            raise ValueError("Flower names must be a collection, not a single string.")  # noqa: TRY004 -- retain v1 behavior
        if any(not isinstance(name, str) or not name.strip() for name in self.flowers):
            raise ValueError("Canonical flower names must be nonempty strings.")
        object.__setattr__(self, "flowers", tuple(dict.fromkeys(self.flowers)))


@dataclass(frozen=True)
class Evidence:
    """A semantic context span; end is an exclusive Python character index."""

    start: int
    end: int
    text: str
    rule_id: str


@dataclass(frozen=True)
class Candidate:
    """An observed candidate, possibly withheld for an explicit reason."""

    value: str | Decimal | None
    evidence: tuple[Evidence, ...]
    reason: str | None = None


@dataclass(frozen=True)
class ExtractedValue:
    """A confirmed value with all its supporting context spans."""

    value: str | Decimal
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class FieldExtraction:
    """Only resolved fields expose confirmed values; candidates remain inspectable."""

    state: ExtractionState
    values: tuple[ExtractedValue, ...] = ()
    candidates: tuple[Candidate, ...] = ()
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryExtraction:
    """Four-field extraction, deliberately not a BouquetInterpretation."""

    size: FieldExtraction
    budget_max: FieldExtraction
    preferred_flowers: FieldExtraction
    excluded_flowers: FieldExtraction
    rules_version: str = RULES_VERSION

    def fields(self) -> dict[str, FieldExtraction]:
        """Expose named fields for the standalone evaluator."""
        return {name: getattr(self, name) for name in FIELDS}

    def to_dict(self) -> dict[str, Any]:
        """Serialize Decimal values losslessly and retain evidence and diagnostics."""
        def encode(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()}
            if isinstance(value, (tuple, list)):
                return [encode(item) for item in value]
            return value

        return encode(asdict(self))
