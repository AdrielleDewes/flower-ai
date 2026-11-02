"""Validate gold approval and annotation integrity without running extraction."""

import json
from collections import Counter
from pathlib import Path

import pytest

from evaluation.query_extractor import QueryExtractor
from evaluation.query_extractor.annotations import load_annotated_dataset

EVALUATION = Path(__file__).parents[1]
GOLD = EVALUATION / "query_extractor" / "gold"


@pytest.mark.parametrize("version,total", [(1, 16), (2, 30)])
def test_gold_drafts_are_complete_and_blocked_pending_approval(version, total):
    """No saved draft may bypass the existing review gate."""
    dataset = EVALUATION / "data" / f"bouquet_requests_v{version}.json"
    path = GOLD / f"bouquet_requests_v{version}_gold_v1.json"
    annotations = json.loads(path.read_text(encoding="utf-8"))
    assert len(annotations["cases"]) == total
    assert all(case["reviewed"] is False for case in annotations["cases"])
    with pytest.raises(ValueError, match="review"):
        load_annotated_dataset(dataset, path)


@pytest.mark.parametrize("version,total", [(1, 16), (2, 30)])
def test_gold_hashes_labels_and_spans_validate_without_inference(
    version, total, tmp_path, monkeypatch,
):
    """A temporary review flag tests structure, not manual approval or quality."""
    def forbid_extraction(self, query):
        raise AssertionError("Gold validation must not invoke QueryExtractor.extract")

    monkeypatch.setattr(QueryExtractor, "extract", forbid_extraction)
    dataset = EVALUATION / "data" / f"bouquet_requests_v{version}.json"
    path = GOLD / f"bouquet_requests_v{version}_gold_v1.json"
    annotations = json.loads(path.read_text(encoding="utf-8"))
    for case in annotations["cases"]:
        case["reviewed"] = True
    validation_copy = tmp_path / "technical_validation_only.json"
    validation_copy.write_text(json.dumps(annotations, ensure_ascii=False), encoding="utf-8")
    prepared = load_annotated_dataset(dataset, validation_copy)
    assert len(prepared.cases) == total
    assert Counter(case.language for case in prepared.cases) == (
        {"pt": 6, "en": 10} if version == 1 else {"pt": 15, "en": 15}
    )
    for case in prepared.cases:
        for field, annotation in case.annotations.items():
            if annotation["state"] == "ABSENT":
                assert annotation["evidence"] == []
            for evidence in annotation["evidence"]:
                assert case.query[evidence["start"]:evidence["end"]] == evidence["text"]
                if field == "excluded_flowers":
                    assert any(cue in evidence["text"].casefold() for cue in (
                        "sem ", "não ", "no ", "nada de ", "avoid ",
                        "leave out ", "excluding ",
                    ))
    # Technical validation must never approve the source artifact in place.
    assert all(case["reviewed"] is False for case in json.loads(path.read_text())["cases"])


def test_gold_records_indecision_separately_from_omission():
    """Null labels are not automatically annotated as absence."""
    path = GOLD / "bouquet_requests_v2_gold_v1.json"
    cases = {case["id"]: case for case in json.loads(path.read_text())["cases"]}
    for case_id in (
        "pt_v2_ambiguous_impact", "pt_v2_size_unsure", "en_v2_ambiguous_size",
        "en_v2_occasion_no_defaults",
    ):
        assert cases[case_id]["fields"]["size"]["state"] == "AMBIGUOUS"
    assert cases["en_v2_occasion_no_defaults"]["fields"]["preferred_flowers"]["state"] == "AMBIGUOUS"
    assert cases["pt_v2_budget_not_size"]["fields"]["size"]["state"] == "ABSENT"
    assert cases["pt_v2_stem_count_not_size"]["fields"]["size"]["state"] == "ABSENT"
    assert cases["pt_v2_pink_is_color"]["fields"]["preferred_flowers"]["state"] == "ABSENT"
    choices = cases["pt_v2_size_unsure"]["fields"]["size"]
    assert [evidence["value"] for evidence in choices["evidence"]] == ["SMALL", "LARGE"]
    assert all("não sei" in evidence["text"] for evidence in choices["evidence"])


def test_unsupported_exclusion_retains_pending_evidence_without_canonical_value():
    """An explicit unmapped exclusion is not silently relabeled as no exclusion."""
    path = GOLD / "bouquet_requests_v2_gold_v1.json"
    cases = {case["id"]: case for case in json.loads(path.read_text())["cases"]}
    excluded = cases["pt_v2_unsupported_flower"]["fields"]["excluded_flowers"]
    assert excluded["state"] == "AMBIGUOUS"
    assert excluded["evidence"][0]["value"] is None
    assert excluded["evidence"][0]["text"] == "sem antúrios"
    mixed = cases["en_v2_unsupported_mixed"]["fields"]["excluded_flowers"]
    assert mixed["state"] == "RESOLVED"
    assert [span["value"] for span in mixed["evidence"]] == ["Rose"]
    assert mixed["evidence"][0]["text"] == "no dahlias or roses"


@pytest.mark.parametrize("representation", ["pending_field", "null_item"])
def test_current_format_cannot_encode_partial_resolution(representation, tmp_path):
    """Document the loader limit without altering production or annotation contracts."""
    dataset = EVALUATION / "data" / "bouquet_requests_v2.json"
    path = GOLD / "bouquet_requests_v2_gold_v1.json"
    annotations = json.loads(path.read_text())
    for case in annotations["cases"]:
        case["reviewed"] = True
    mixed = next(case for case in annotations["cases"] if case["id"] == "en_v2_unsupported_mixed")
    excluded = mixed["fields"]["excluded_flowers"]
    if representation == "pending_field":
        excluded["state"] = "AMBIGUOUS"
    else:
        excluded["evidence"].append({**excluded["evidence"][0], "value": None})
    candidate = tmp_path / "unsupported_partial_representation.json"
    candidate.write_text(json.dumps(annotations), encoding="utf-8")
    with pytest.raises(ValueError):
        load_annotated_dataset(dataset, candidate)


@pytest.mark.parametrize("version,total", [(1, 16), (2, 30)])
def test_gold_v2_validates_without_extraction_and_preserves_v1(
    version, total, tmp_path, monkeypatch,
):
    """Validate all real gold cases structurally without evaluating the extractor."""
    def forbidden(self, query):
        raise AssertionError("No extraction during gold migration validation")

    monkeypatch.setattr(QueryExtractor, "extract", forbidden)
    dataset = EVALUATION / "data" / f"bouquet_requests_v{version}.json"
    v1_path = GOLD / f"bouquet_requests_v{version}_gold_v1.json"
    v1_bytes = v1_path.read_bytes()
    v1 = json.loads(v1_bytes)
    path = GOLD / f"bouquet_requests_v{version}_gold_v2.json"
    v2_bytes = path.read_bytes()
    v2 = json.loads(v2_bytes)
    assert v2["annotation_version"] == 2
    assert v1["dataset_sha256"] == v2["dataset_sha256"]
    assert [c["id"] for c in v1["cases"]] == [c["id"] for c in v2["cases"]]
    # Explicit user approval applies only to gold_v2; gold_v1 stays unapproved.
    assert all(case["reviewed"] is True for case in v2["cases"])
    prepared = load_annotated_dataset(dataset, path)
    v2["cases"][0]["reviewed"] = False
    candidate = tmp_path / "v2_unapproved_case.json"
    candidate.write_text(json.dumps(v2), encoding="utf-8")
    with pytest.raises(ValueError, match="review"):
        load_annotated_dataset(dataset, candidate)
    assert prepared.annotation_version == 2
    assert len(prepared.cases) == total
    fields = [f for case in prepared.cases for f in case.annotations.values()]
    states = Counter(field["state"] for field in fields)
    assert states == (
        {"ABSENT": 40, "RESOLVED": 24} if version == 1 else
        {"ABSENT": 60, "RESOLVED": 51, "PARTIAL": 3, "AMBIGUOUS": 6}
    )
    reasons = Counter(m["reason"] for field in fields for m in field["unresolved_mentions"])
    assert reasons == ({} if version == 1 else {"OUT_OF_CATALOG": 4, "UNDECIDED": 5})
    assert path.read_bytes() == v2_bytes
    assert v1_path.read_bytes() == v1_bytes


def test_gold_v2_represents_known_values_and_unmapped_mentions_independently():
    """The four unavailable flower mentions remain literal evidence, not inventions."""
    path = GOLD / "bouquet_requests_v2_gold_v2.json"
    cases = {case["id"]: case for case in json.loads(path.read_text())["cases"]}
    expected = [
        ("pt_v2_unsupported_flower", "preferred_flowers", "PARTIAL", ["Rose"], "orquídeas"),
        ("pt_v2_unsupported_flower", "excluded_flowers", "AMBIGUOUS", [], "antúrios"),
        ("en_v2_unsupported_mixed", "preferred_flowers", "PARTIAL", ["Tulip"], "orchids"),
        ("en_v2_unsupported_mixed", "excluded_flowers", "PARTIAL", ["Rose"], "dahlias"),
    ]
    for case_id, name, state, values, raw_name in expected:
        field = cases[case_id]["fields"][name]
        assert field["state"] == state
        assert [value["value"] for value in field["resolved_values"]] == values
        assert field["unresolved_mentions"][0]["reason"] == "OUT_OF_CATALOG"
        assert field["unresolved_mentions"][0]["mention"]["text"] == raw_name
        assert field["unresolved_mentions"][0]["candidates"] == []
