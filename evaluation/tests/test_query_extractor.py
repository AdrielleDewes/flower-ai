"""Focused synthetic queries, not a run of the 46-case extraction benchmark."""

import ast
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from evaluation.query_extractor import ExtractionState, FlowerVocabulary, QueryExtractor
from evaluation.query_extractor.text import tokens
from evaluation.query_extractor.vocabulary import CatalogMatcher


@pytest.fixture
def extractor():
    """Use a small catalog to test rule behavior and tenant boundaries."""
    return QueryExtractor(FlowerVocabulary(("Rose", "Lily", "Tulip", "Baby's Breath")))


def values(result, field):
    """Read only confirmed values, never diagnostic candidates."""
    return [item.value for item in getattr(result, field).values]


@pytest.mark.parametrize("text,size", [
    ("Quero um buquê pequeno com rosas.", "SMALL"),
    ("A medium bouquet, please.", "MEDIUM"),
    ("Buquê grande.", "LARGE"),
    ("Small please", "SMALL"),
    ("tamanho: médio", "MEDIUM"),
    ("Quero buquês pequenos", "SMALL"),
])
def test_explicit_sizes_with_semantic_context(extractor, text, size):
    """Sizes describe the bouquet or an explicit size selection."""
    assert values(extractor.extract(text), "size") == [size]


@pytest.mark.parametrize("text", [
    "R$400 de orçamento", "Quero 25 rosas", "A large vase with roses",
    "A small delivery van", "The large bouquet has roses", 'She said "a small bouquet"',
])
def test_size_is_not_inferred_or_taken_from_other_referents(extractor, text):
    """Numbers and adjectives in nonrequest contexts do not confirm size."""
    assert not extractor.extract(text).size.values


@pytest.mark.parametrize("text,state", [
    ("Small or large bouquet", ExtractionState.AMBIGUOUS),
    ("Ainda não sei se pequeno ou grande.", ExtractionState.AMBIGUOUS),
    ("Not a small bouquet", ExtractionState.AMBIGUOUS),
    ("Small bouquet. Large bouquet.", ExtractionState.CONFLICT),
    ("Small bouquet, actually a large bouquet", ExtractionState.CONFLICT),
])
def test_unresolved_sizes_are_not_silently_chosen(extractor, text, state):
    """Alternatives and conflicting assertions preserve evidence without values."""
    result = extractor.extract(text).size
    assert result.state is state
    assert not result.values
    assert result.candidates


@pytest.mark.parametrize("text,amount", [
    ("Posso gastar até R$87,50.", "87.50"),
    ("My budget is 120.25 reais", "120.25"),
    ("Budget: BRL 90", "90"),
    ("A bouquet under R$60", "60"),
    ("Orçamento entre R$50 e R$85", "85"),
    ("Budget between 45 and 105 reais", "105"),
    ("Até R$1.234,50", "1234.50"),
    ("Budget up to R$1,234.50", "1234.50"),
])
def test_explicit_budget_limits_use_decimal(extractor, text, amount):
    """Money requires a currency or budget context and a recognized limit rule."""
    assert values(extractor.extract(text), "budget_max") == [Decimal(amount)]


@pytest.mark.parametrize("text", [
    "Deliver at 14:30 to apartment 150", "Quero até 12 rosas",
    "My budget is at least R$90", "Budget over R$50",
    "Não é meu orçamento: 150", "Quero cento e cinquenta reais",
])
def test_irrelevant_or_unsupported_numbers_do_not_become_upper_budgets(extractor, text):
    """Minimums and quantities must not be reinterpreted as maximum prices."""
    assert not extractor.extract(text).budget_max.values


@pytest.mark.parametrize("text,state", [
    ("Budget up to R$1.000", ExtractionState.AMBIGUOUS),
    ("Budget up to USD100", ExtractionState.AMBIGUOUS),
    ("Budget up to 100 dollars", ExtractionState.AMBIGUOUS),
    ("Maybe a budget of R$50", ExtractionState.AMBIGUOUS),
    ("Budget R$0", ExtractionState.AMBIGUOUS),
    ("Budget R$50 or R$70", ExtractionState.AMBIGUOUS),
    ("Até R$100. Até R$200.", ExtractionState.CONFLICT),
])
def test_ambiguous_or_conflicting_money_remains_pending(extractor, text, state):
    """No conversion, guessed separators or automatic minimum of multiple limits."""
    result = extractor.extract(text).budget_max
    assert result.state is state
    assert not result.values


@pytest.mark.parametrize("text,preferred,excluded", [
    ("Quero rosas e tulipas, sem lírios", ["Rose", "Tulip"], ["Lily"]),
    ("Use lilies, and avoid roses and tulips", ["Lily"], ["Rose", "Tulip"]),
    ("Não coloque lírios nem tulipas", [], ["Lily", "Tulip"]),
    ("No roses. With lilies.", ["Lily"], ["Rose"]),
    ("Roses and tulips", ["Rose", "Tulip"], []),
    ("Com uma rosa", ["Rose"], []),
    ("With baby's breath and lilies", ["Baby's Breath", "Lily"], []),
    ("Com mosquitinhos e rosas", ["Baby's Breath", "Rose"], []),
    ("With orchids and roses", ["Rose"], []),
    ("Do not use roses", [], ["Rose"]),
    ("Sem rosas e com lírios", ["Lily"], ["Rose"]),
    ("I want roses, not lilies", ["Rose"], ["Lily"]),
    ("I cannot use roses", [], ["Rose"]),
])
def test_flower_relations_and_coordinated_negation(extractor, text, preferred, excluded):
    """Evidence establishes requested inclusion/exclusion, not just word presence."""
    result = extractor.extract(text)
    assert values(result, "preferred_flowers") == preferred
    assert values(result, "excluded_flowers") == excluded


@pytest.mark.parametrize("text", [
    "A pink bouquet", "Quero um buquê em tons de rosa",
    "Minha mãe gosta de rosas", "She arrived with roses",
    "The vase has lilies", "No preference for roses", "roseship and tulipwood",
    'I quote "with roses"', "A ribbon with roses", "rose-colored wrapping",
])
def test_unrelated_ambiguous_or_quoted_mentions_are_not_preferences(extractor, text):
    """Do not extract matching names without the intended semantic relation."""
    result = extractor.extract(text)
    assert not result.preferred_flowers.values
    assert not result.excluded_flowers.values


@pytest.mark.parametrize("text", [
    "Maybe use roses", "Use roses or tulips", "Not without roses", "Do not avoid roses",
    "I don't want to avoid roses", "I might use roses", "If possible, use roses",
])
def test_uncertain_polarity_or_choice_does_not_confirm_flowers(extractor, text):
    """Keep uncertainty in at least one diagnostic field without assigning values."""
    result = extractor.extract(text)
    assert not result.preferred_flowers.values
    assert not result.excluded_flowers.values
    assert any(field.state is ExtractionState.AMBIGUOUS for field in result.fields().values())


def test_requested_and_excluded_flower_marks_both_fields_conflicted(extractor):
    """No last-mention-wins behavior, including purported corrections."""
    result = extractor.extract("Use roses and lilies. Actually, no roses.")
    for field in (result.preferred_flowers, result.excluded_flowers):
        assert field.state is ExtractionState.CONFLICT
        assert not field.values
        assert field.candidates


def test_evidence_offsets_context_and_deduplication(extractor):
    """Spans preserve accents, spacing and the semantic cue for each value."""
    text = "  Quero LÍRIOS. Com lírios; sem rosas. Orçamento até R$95,50!"
    result = extractor.extract(text)
    assert values(result, "preferred_flowers") == ["Lily"]
    assert len(result.preferred_flowers.values[0].evidence) == 2
    assert result.excluded_flowers.values[0].evidence[0].text == "sem rosas"
    for field in result.fields().values():
        for candidate in field.candidates:
            for evidence in candidate.evidence:
                assert text[evidence.start:evidence.end] == evidence.text
                assert evidence.rule_id
    assert result.to_dict()["budget_max"]["values"][0]["value"] == "95.50"
    assert extractor.extract(text) == result


def test_catalog_snapshot_and_unavailable_aliases():
    """Available canonical names are authoritative and cannot leak between catalogs."""
    names = ["Rose"]
    first = QueryExtractor(FlowerVocabulary(names))
    names.append("Lily")
    second = QueryExtractor(FlowerVocabulary(("Lily",)))
    assert values(first.extract("With roses and lilies"), "preferred_flowers") == ["Rose"]
    assert values(second.extract("With roses and lilies"), "preferred_flowers") == ["Lily"]


def test_longest_match_and_alias_collision_are_visible():
    """Prefer compound names but retain ambiguity instead of arbitrary resolution."""
    matcher = CatalogMatcher(
        FlowerVocabulary(("Rose", "Wild Rose")),
        aliases={"Rose": ("shared",), "Wild Rose": ("shared",)},
    )
    matches = matcher.find(tokens("Wild Rose and shared"))
    assert matches[0].names == ("Wild Rose",)
    assert matches[1].names == ("Rose", "Wild Rose")


def test_core_has_no_application_or_external_dependencies():
    """The experiment cannot import the LLM, canonical schemas or recommendation."""
    root = Path(__file__).parents[2] / "backend" / "app" / "services" / "query_extractor"
    allowed = sys.stdlib_module_names
    for path in root.glob("*.py"):
        if path.name in {"evaluation.py", "__main__.py"}:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in allowed for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                assert node.module.split(".")[0] in allowed


def test_evaluation_compatibility_exports_share_the_runtime_core():
    """Evaluation reuses the exact runtime classes instead of a second implementation."""
    from app.services.query_extractor import QueryExtractor as RuntimeExtractor
    from app.services.query_extractor.contracts import ExtractionState as RuntimeState

    assert QueryExtractor is RuntimeExtractor
    assert ExtractionState is RuntimeState


def test_empty_query_and_invalid_input(extractor):
    """No default preferences appear for empty input."""
    assert all(f.state is ExtractionState.ABSENT for f in extractor.extract(" ").fields().values())
    with pytest.raises(TypeError):
        extractor.extract(None)


def test_decomposed_unicode_and_canonical_alias_collision():
    """Unicode folding must not lose offsets or choose a normalized-name collision."""
    text = "Com li\u0301rios"
    extractor = QueryExtractor(FlowerVocabulary(("Lily",)))
    result = extractor.extract(text)
    assert values(result, "preferred_flowers") == ["Lily"]
    evidence = result.preferred_flowers.values[0].evidence[0]
    assert text[evidence.start:evidence.end] == text
    collision = QueryExtractor(FlowerVocabulary(("Rose", "ROSE"))).extract("With rose")
    assert collision.preferred_flowers.state is ExtractionState.AMBIGUOUS
    assert not collision.preferred_flowers.values


@pytest.mark.parametrize("text", ["Budget 1e3", "Budget R$100..50", "Budget R$100,000"])
def test_partial_numeric_matches_are_not_confirmed(extractor, text):
    """A malformed or unsupported numeral must not be truncated to a smaller amount."""
    assert not extractor.extract(text).budget_max.values
