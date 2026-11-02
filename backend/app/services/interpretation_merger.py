"""Deterministic, conservative source combination; no inference or persistence."""

from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog
from app.schemas.interpretation import (
    FieldSources,
    InterpretationEvidence,
    InterpretationField,
    InterpretationMergeResult,
    InterpretationValue,
    ReviewIssue,
    SourceRelation,
)
from app.services.bouquet_interpretation import (
    assess_bouquet_interpretation,
    to_bouquet_request,
)
from app.services.catalog_validation import validate_budget_max, validate_catalog_values
from app.services.query_extractor.contracts import ExtractionState, QueryExtraction


def _issue(field: InterpretationField, code: str, message: str) -> ReviewIssue:
    """Build a client-review issue without exposing provider or evaluation details."""
    return ReviewIssue(field=field, code=code, message=message)


def _merge_lists(
    field: InterpretationField, llm: list[str], explicit: list[str],
) -> tuple[list[str] | None, SourceRelation, ReviewIssue | None]:
    """Accept evidenced additions, but never silently confirm LLM-only additions."""
    left, right = set(llm), set(explicit)
    common = left & right
    llm_common = [value for value in llm if value in common]
    explicit_common = [value for value in explicit if value in common]
    if llm_common != explicit_common:
        return None, SourceRelation.DIVERGENCE, _issue(
            field, "LIST_ORDER_DIVERGENCE", "Review the order of the proposed values.",
        )
    if left <= right:
        # Explicit, resolved additions do not contradict an incomplete model list.
        return explicit, SourceRelation.COMPLEMENTARY, None
    if right < left:
        return explicit, SourceRelation.COMPLEMENTARY, _issue(
            field, "UNCONFIRMED_LLM_VALUES", "Review additional values proposed only by the language model.",
        )
    return explicit_common or None, SourceRelation.DIVERGENCE, _issue(
        field, "LIST_DIVERGENCE", "Review the differing proposed values; they are not necessarily contradictory.",
    )


def _resolved_interpretation(extraction: QueryExtraction) -> BouquetInterpretation:
    """Map only RESOLVED values into the canonical schema, never diagnostic candidates."""
    values = {}
    for name, result in extraction.fields().items():
        if result.state is not ExtractionState.RESOLVED:
            continue
        confirmed = [item.value for item in result.values]
        if not confirmed or (name in {"size", "budget_max"} and len(confirmed) != 1):
            raise ValueError("Invalid resolved extractor value count.")
        values[name] = confirmed[0] if name in {"size", "budget_max"} else confirmed
    return BouquetInterpretation.model_validate(values)


def _field_value(
    field: InterpretationField, llm: InterpretationValue, explicit: InterpretationValue,
    state: ExtractionState | None,
) -> tuple[InterpretationValue, SourceRelation, ReviewIssue | None]:
    """Keep extraction uncertainty distinct from failure to identify information."""
    if state in {ExtractionState.AMBIGUOUS, ExtractionState.CONFLICT}:
        conflict = state is ExtractionState.CONFLICT
        return None, SourceRelation.CONTRADICTION if conflict else SourceRelation.UNRESOLVED, _issue(
            field, "EXTRACTOR_CONFLICT" if conflict else "EXTRACTOR_UNCERTAIN",
            "Review the explicit conflicting statements." if conflict else "Clarify this part of the request.",
        )
    if llm is None and explicit is None:
        return None, SourceRelation.NOT_IDENTIFIED, None
    if llm is None or explicit is None:
        return explicit if explicit is not None else llm, SourceRelation.COMPLEMENTARY, None
    if llm == explicit:
        return explicit, SourceRelation.AGREEMENT, None
    if isinstance(llm, list) and isinstance(explicit, list):
        return _merge_lists(field, llm, explicit)
    budget = field == "budget_max"
    return None, SourceRelation.DIVERGENCE if budget else SourceRelation.CONTRADICTION, _issue(
        field, "BUDGET_DIVERGENCE" if budget else "SCALAR_CONTRADICTION",
        "Review the differing budget limits." if budget else "Choose between the incompatible values.",
    )


def merge_interpretations(
    llm: BouquetInterpretation, extraction: QueryExtraction, catalog: InterpretationCatalog,
) -> InterpretationMergeResult:
    """Produce a reviewable canonical draft without resolving uncertain constraints."""
    explicit = _resolved_interpretation(extraction)
    for source in (llm, explicit):
        validate_catalog_values(source, catalog)
        validate_budget_max(source.budget_max)
    fields = extraction.fields()
    merged, sources, issues = {}, {}, []
    for name in BouquetInterpretation.model_fields:
        llm_value, extractor_value = getattr(llm, name), getattr(explicit, name)
        result = fields.get(name)
        value, relation, issue = _field_value(
            name, llm_value, extractor_value, result.state if result else None,
        )
        merged[name] = value
        spans = []
        if result:
            # Uncertain candidates supply context only, never confirmed values.
            for candidate in (*result.values, *result.candidates):
                for evidence in candidate.evidence:
                    span = InterpretationEvidence(start=evidence.start, end=evidence.end, text=evidence.text)
                    if span not in spans:
                        spans.append(span)
        sources[name] = FieldSources(
            relation=relation, llm_value=llm_value, extractor_value=extractor_value, evidence=spans,
        )
        if issue:
            issues.append(issue)
    preferred = set(llm.preferred_flowers or []) | set(explicit.preferred_flowers or [])
    excluded = set(llm.excluded_flowers or []) | set(explicit.excluded_flowers or [])
    if preferred & excluded:
        for name in ("preferred_flowers", "excluded_flowers"):
            merged[name] = None
            sources[name].relation = SourceRelation.CONTRADICTION
        issues.append(ReviewIssue(
            field="preferred_flowers", related_fields=["excluded_flowers"],
            code="PREFERENCE_EXCLUSION_CONFLICT",
            message="A flower is both preferred and excluded; review both fields.",
        ))
    interpretation = BouquetInterpretation.model_validate(merged)
    validate_catalog_values(interpretation, catalog)
    readiness = assess_bouquet_interpretation(interpretation)
    requires_review = bool(issues or readiness.missing_fields)
    return InterpretationMergeResult(
        interpretation=interpretation, readiness=readiness, issues=issues,
        field_sources=sources, requires_review=requires_review,
        recommendation_request=None if requires_review else to_bouquet_request(interpretation),
    )
