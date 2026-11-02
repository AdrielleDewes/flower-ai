"""Deterministic merger behavior with synthetic, evidence-bearing source values."""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog
from app.services.catalog_validation import CatalogValidationError
from app.services.interpretation_merger import merge_interpretations
from app.services.query_extractor import FlowerVocabulary, QueryExtractor
from app.services.query_extractor.contracts import (
    Candidate,
    Evidence,
    ExtractedValue,
    ExtractionState,
    FieldExtraction,
)

CATALOG = InterpretationCatalog(
    occasions=["Birthday"], styles=["Modern"], colors=["Red"], flowers=["Rose", "Lily", "Tulip"],
)
COMPLETE = {"occasion": "Birthday", "styles": ["Modern"], "colors": ["Red"], "size": "SMALL"}


def extraction(**overrides):
    """Build controlled source states without depending on language-rule coverage."""
    empty = QueryExtractor(FlowerVocabulary(tuple(CATALOG.flowers))).extract("")
    return replace(empty, **overrides)


def resolved(*values):
    """Attach source context to explicit values for preservation tests."""
    evidence = (Evidence(0, 14, "explicit query", "test.explicit"),)
    return FieldExtraction(
        ExtractionState.RESOLVED,
        values=tuple(ExtractedValue(value, evidence) for value in values),
        candidates=tuple(Candidate(value, evidence) for value in values),
    )


def test_agreement_complete_draft_does_not_require_issue_review():
    """Frontend confirmation is separate from the presence of unresolved issues."""
    llm = BouquetInterpretation(**COMPLETE, budget_max="90", preferred_flowers=["Rose"])
    explicit = extraction(size=resolved("SMALL"), budget_max=resolved(Decimal("90.00")), preferred_flowers=resolved("Rose"))
    result = merge_interpretations(llm, explicit, CATALOG)
    assert result.requires_review is False
    assert result.recommendation_request.size.value == "SMALL"
    assert result.recommendation_request.budget_max == Decimal(90)
    assert result.field_sources["size"].relation.value == "AGREEMENT"
    assert result.field_sources["preferred_flowers"].llm_value == ["Rose"]
    assert result.field_sources["preferred_flowers"].extractor_value == ["Rose"]
    assert result.field_sources["preferred_flowers"].evidence[0].text == "explicit query"


@pytest.mark.parametrize("field,value", [("size", "SMALL"), ("budget_max", Decimal(40)), ("preferred_flowers", "Rose"), ("excluded_flowers", "Lily")])
def test_resolved_values_complement_missing_model_information(field, value):
    llm = BouquetInterpretation(**{**COMPLETE, field: None})
    result = merge_interpretations(llm, extraction(**{field: resolved(value)}), CATALOG)
    expected = [value] if field.endswith("flowers") else value
    assert getattr(result.interpretation, field) == expected
    assert result.field_sources[field].relation.value == "COMPLEMENTARY"
    assert result.requires_review is False


def test_absent_extraction_is_not_proof_of_absence():
    llm = BouquetInterpretation(**COMPLETE, preferred_flowers=["Tulip"])
    result = merge_interpretations(llm, extraction(), CATALOG)
    assert result.interpretation.preferred_flowers == ["Tulip"]
    assert result.interpretation.excluded_flowers is None
    assert result.requires_review is False
    assert result.field_sources["excluded_flowers"].relation.value == "NOT_IDENTIFIED"


@pytest.mark.parametrize("state", [ExtractionState.AMBIGUOUS, ExtractionState.CONFLICT])
def test_abstentions_do_not_turn_candidates_into_confirmed_values(state):
    uncertain = FieldExtraction(
        state, candidates=(Candidate("Rose", (Evidence(0, 8, "uncertain", "test"),), "uncertain"),),
        reasons=("uncertain",),
    )
    result = merge_interpretations(
        BouquetInterpretation(**COMPLETE, preferred_flowers=["Rose"]),
        extraction(preferred_flowers=uncertain), CATALOG,
    )
    assert result.interpretation.preferred_flowers is None
    assert result.field_sources["preferred_flowers"].extractor_value is None
    assert result.field_sources["preferred_flowers"].llm_value == ["Rose"]
    assert result.field_sources["preferred_flowers"].evidence[0].text == "uncertain"
    assert result.readiness.status.value == "READY"
    assert result.requires_review is True
    assert result.recommendation_request is None


@pytest.mark.parametrize("llm,explicit,expected,relation,issue", [
    (["Rose"], ["Rose", "Lily"], ["Rose", "Lily"], "COMPLEMENTARY", None),
    (["Rose", "Lily"], ["Rose"], ["Rose"], "COMPLEMENTARY", "UNCONFIRMED_LLM_VALUES"),
    (["Rose", "Lily"], ["Rose", "Tulip"], ["Rose"], "DIVERGENCE", "LIST_DIVERGENCE"),
    (["Rose"], ["Lily"], None, "DIVERGENCE", "LIST_DIVERGENCE"),
    (["Lily", "Rose"], ["Rose", "Lily"], None, "DIVERGENCE", "LIST_ORDER_DIVERGENCE"),
])
def test_list_relationships_are_not_all_contradictions(llm, explicit, expected, relation, issue):
    result = merge_interpretations(
        BouquetInterpretation(**COMPLETE, preferred_flowers=llm),
        extraction(preferred_flowers=resolved(*explicit)), CATALOG,
    )
    assert result.interpretation.preferred_flowers == expected
    assert result.field_sources["preferred_flowers"].relation.value == relation
    assert result.field_sources["preferred_flowers"].llm_value == llm
    assert result.field_sources["preferred_flowers"].extractor_value == explicit
    assert [i.code for i in result.issues] == ([issue] if issue else [])
    assert result.requires_review is bool(issue)


def test_different_budgets_are_divergent_without_choosing_the_minimum():
    result = merge_interpretations(
        BouquetInterpretation(**COMPLETE, budget_max="100"), extraction(budget_max=resolved(Decimal(80))), CATALOG,
    )
    assert result.interpretation.budget_max is None
    assert result.field_sources["budget_max"].relation.value == "DIVERGENCE"
    assert result.issues[0].code == "BUDGET_DIVERGENCE"
    assert result.requires_review is True


def test_mutually_exclusive_sizes_are_a_contradiction():
    result = merge_interpretations(
        BouquetInterpretation(**COMPLETE), extraction(size=resolved("LARGE")), CATALOG,
    )
    assert result.interpretation.size is None
    assert result.field_sources["size"].relation.value == "CONTRADICTION"
    assert result.readiness.missing_fields == ["size"]
    assert result.requires_review is True


@pytest.mark.parametrize("llm_fields,core_fields", [
    ({"preferred_flowers": ["Rose"]}, {"excluded_flowers": resolved("Rose")}),
    ({"preferred_flowers": ["Rose"], "excluded_flowers": ["Rose"]}, {}),
    ({"preferred_flowers": ["Rose", "Lily"]}, {"preferred_flowers": resolved("Rose"), "excluded_flowers": resolved("Lily")}),
])
def test_actual_inclusion_exclusion_contradictions_are_never_resolved_silently(llm_fields, core_fields):
    result = merge_interpretations(BouquetInterpretation(**COMPLETE, **llm_fields), extraction(**core_fields), CATALOG)
    assert result.interpretation.preferred_flowers is None
    assert result.interpretation.excluded_flowers is None
    assert any(i.code == "PREFERENCE_EXCLUSION_CONFLICT" for i in result.issues)
    assert result.requires_review is True
    assert result.recommendation_request is None


@pytest.mark.parametrize("source", ["llm", "extractor"])
def test_invalid_catalog_values_cannot_be_hidden_by_the_merge(source):
    llm = BouquetInterpretation(**COMPLETE, preferred_flowers=["Unknown"] if source == "llm" else None)
    core = extraction(preferred_flowers=resolved("Unknown")) if source == "extractor" else extraction()
    with pytest.raises(CatalogValidationError):
        merge_interpretations(llm, core, CATALOG)


def test_missing_required_fields_require_review_without_invented_values():
    result = merge_interpretations(BouquetInterpretation(), extraction(), CATALOG)
    assert result.readiness.missing_fields == ["occasion", "styles", "colors", "size"]
    assert result.requires_review is True
    assert result.recommendation_request is None


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_invalid_budget_does_not_reach_recommendation_preview(amount):
    with pytest.raises(ValueError, match="budget_max"):
        merge_interpretations(BouquetInterpretation(**COMPLETE, budget_max=amount), extraction(), CATALOG)
