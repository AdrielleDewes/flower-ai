"""Synthetic v2 annotation/metric tests; no 46-case extraction benchmark."""

import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from evaluation.query_extractor import QueryExtractor
from evaluation.query_extractor.__main__ import main
from evaluation.query_extractor.annotation_v2 import (
    AnnotationPrediction,
    validate_field_v2,
)
from evaluation.query_extractor.annotations import (
    annotation_template,
    load_annotated_dataset,
)
from evaluation.query_extractor.evaluation import evaluate_extractor
from evaluation.query_extractor.migration import migrate_annotations_v1


def span(query, text):
    """Locate an explicitly selected support phrase in a synthetic query."""
    start = query.index(text)
    return {"start": start, "end": start + len(text), "text": text}


def pending(query, mention, evidence, reason, candidates=()):
    """Construct a pending annotation independently from any extraction rule."""
    return {
        "reason": reason, "mention": span(query, mention), "candidates": list(candidates),
        "evidence": [span(query, evidence)],
    }


def empty():
    """Represent an absent field without positive evidence."""
    return {"state": "ABSENT", "resolved_values": [], "unresolved_mentions": []}


@pytest.fixture
def v2_files(tmp_path):
    """Four synthetic cases exercise complete, partial, undecided and conflict states."""
    raw = [
        ("pt", "Com rosas e orquídeas. Sem antúrios.", (None, None, ["Rose"], None)),
        ("en", "A small bouquet. Budget up to R$30", ("SMALL", "30", None, None)),
        ("en", "Small or large bouquet", (None, None, None, None)),
        ("en", "Small bouquet. Large bouquet.", (None, None, None, None)),
    ]
    fields = ("size", "budget_max", "preferred_flowers", "excluded_flowers")
    dataset = {
        "version": 2, "catalog": {"flowers": ["Rose", "Lily"]},
        "cases": [{"id": f"synthetic_{i}", "input": text, "expected": dict(zip(fields, values, strict=True))}
                  for i, (_, text, values) in enumerate(raw)],
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False))
    annotations = annotation_template(path, annotation_version=2)
    for case, (language, _, _) in zip(annotations["cases"], raw, strict=True):
        case.update(language=language, reviewed=True)
        case["fields"] = {field: empty() for field in fields}
    q = raw[0][1]
    annotations["cases"][0]["fields"]["preferred_flowers"] = {
        "state": "PARTIAL", "resolved_values": [{"value": "Rose", "evidence": [span(q, "Com rosas e orquídeas")]}],
        "unresolved_mentions": [pending(q, "orquídeas", "Com rosas e orquídeas", "OUT_OF_CATALOG")],
    }
    annotations["cases"][0]["fields"]["excluded_flowers"] = {
        "state": "AMBIGUOUS", "resolved_values": [],
        "unresolved_mentions": [pending(q, "antúrios", "Sem antúrios", "OUT_OF_CATALOG")],
    }
    for field, value, phrase in [("size", "SMALL", "A small bouquet"), ("budget_max", "30", "Budget up to R$30")]:
        annotations["cases"][1]["fields"][field] = {
            "state": "RESOLVED", "resolved_values": [{"value": value, "evidence": [span(raw[1][1], phrase)]}],
            "unresolved_mentions": [],
        }
    for index, state, reason in [(2, "AMBIGUOUS", "UNDECIDED"), (3, "CONFLICT", "CONFLICTING_INFORMATION")]:
        q = raw[index][1]
        annotations["cases"][index]["fields"]["size"] = {
            "state": state, "resolved_values": [],
            "unresolved_mentions": [pending(q, q, q, reason, ("SMALL", "LARGE"))],
        }
    sidecar = tmp_path / "annotations.json"
    sidecar.write_text(json.dumps(annotations, ensure_ascii=False))
    return path, sidecar


def load(v2_files):
    """Load test-only reviewed annotations."""
    return load_annotated_dataset(*v2_files)


def test_v2_all_states_and_perfect_prediction_metrics(v2_files):
    """Scoring supports PARTIAL, but does not call a real extractor or dataset."""
    prepared = load(v2_files)

    class PerfectPrediction:
        def extract(self, query):
            return AnnotationPrediction(deepcopy(next(c.annotations for c in prepared.cases if c.query == query)))

    readings = iter([0, .1, 1, 1.1, 2, 2.1, 3, 3.1])
    report = evaluate_extractor(prepared, PerfectPrediction(), clock=lambda: next(readings))
    assert report["evaluation_version"] == report["annotation_version"] == 2
    group = report["groups"]["all"]
    canonical = group["all_fields"]["canonical_values"]
    assert (canonical["tp"], canonical["fp"], canonical["fn"]) == (3, 0, 0)
    assert canonical["precision"] == canonical["recall"] == 1
    assert "state_accuracy" not in canonical
    pendencies = group["all_fields"]["pending_mentions"]
    assert pendencies["all"]["tp"] == 4
    assert pendencies["by_reason"]["OUT_OF_CATALOG"]["tp"] == 2
    assert pendencies["by_reason"]["UNDECIDED"]["tp"] == 1
    assert pendencies["by_reason"]["CONFLICTING_INFORMATION"]["tp"] == 1
    assert group["canonical_exact_match"]["rate"] == group["semantic_exact_match"]["rate"] == 1
    completeness = group["all_fields"]["completeness"]
    assert completeness["expected_states"]["PARTIAL"] == 1
    assert completeness["claimed_complete_fields"] == 12
    assert completeness["state_accuracy"] == completeness["value_field_coverage"] == 1
    assert report["evidence"]["span_integrity"] == 1
    assert report["timing"]["mean_extraction_seconds"] == pytest.approx(.1)
    assert report["legacy_prediction_cases"] == 0


def test_legacy_rules_do_not_gain_pending_detections_from_gold(v2_files):
    """Absent diagnostic capability produces FN, not gold-assisted output."""
    prepared = load(v2_files)
    report = evaluate_extractor(prepared, QueryExtractor(prepared.catalog))
    assert report["legacy_prediction_cases"] == 4
    assert all(not c["pending_mentions_supported"] for c in report["cases"])
    pending_scores = report["groups"]["all"]["all_fields"]["pending_mentions"]["all"]
    assert (pending_scores["tp"], pending_scores["fp"], pending_scores["fn"]) == (0, 0, 4)
    assert pending_scores["precision"] is None
    assert pending_scores["recall"] == 0
    first = report["cases"][0]
    assert first["canonical_exact_match"] is True
    assert first["semantic_exact_match"] is False
    assert "candidates" in first["actual"]["preferred_flowers"]


@pytest.mark.parametrize("change", ["reason", "span", "candidates"])
def test_pending_reason_span_and_candidates_have_distinct_scoring(v2_files, change):
    """A wrong reason/span yields FP+FN; wrong alternatives fail semantic exact."""
    prepared = load(v2_files)
    case = prepared.cases[2]
    prepared = replace(prepared, cases=(case,))
    output = deepcopy(case.annotations)
    item = output["size"]["unresolved_mentions"][0]
    if change == "reason":
        output["size"]["state"] = "CONFLICT"
        item["reason"] = "CONFLICTING_INFORMATION"
    elif change == "span":
        item["mention"] = span(case.query, "Small")
    else:
        item["candidates"] = ["SMALL"]

    class WrongPending:
        def extract(self, query):
            return AnnotationPrediction(output)

    report = evaluate_extractor(prepared, WrongPending())
    group = report["groups"]["all"]
    assert group["canonical_exact_match"]["rate"] == 1
    assert group["semantic_exact_match"]["rate"] == 0
    pending_scores = group["all_fields"]["pending_mentions"]["all"]
    assert pending_scores["tp"] == (1 if change == "candidates" else 0)
    assert pending_scores["fp"] == pending_scores["fn"] == (0 if change == "candidates" else 1)


def test_canonical_wrong_value_counts_fp_fn_without_changing_pending_scores(v2_files):
    """Canonical quality is independent of correctly acknowledging unsupported text."""
    prepared = load(v2_files)
    prepared = replace(prepared, cases=prepared.cases[:1])
    output = deepcopy(prepared.cases[0].annotations)
    output["preferred_flowers"]["resolved_values"][0]["value"] = "Lily"

    class WrongValue:
        def extract(self, query):
            return AnnotationPrediction(output)

    report = evaluate_extractor(prepared, WrongValue())
    field = report["groups"]["pt"]["fields"]["preferred_flowers"]
    assert field["canonical_values"]["fp"] == field["canonical_values"]["fn"] == 1
    assert field["pending_mentions"]["all"]["recall"] == 1
    assert field["completeness"]["semantic_exact_match_rate"] == 0


def test_v2_decimal_predictions_remain_json_serializable(v2_files):
    """Different decimal spellings compare numerically without losing report precision."""
    prepared = load(v2_files)
    prepared = replace(prepared, cases=prepared.cases[1:2])
    output = deepcopy(prepared.cases[0].annotations)
    output["budget_max"]["resolved_values"][0]["value"] = Decimal("30.00")

    class DecimalPrediction:
        def extract(self, query):
            return AnnotationPrediction(output)

    report = evaluate_extractor(prepared, DecimalPrediction())
    restored = json.loads(json.dumps(report))
    assert restored["cases"][0]["actual"]["budget_max"]["resolved_values"][0]["value"] == "30.00"
    assert restored["groups"]["all"]["semantic_exact_match"]["rate"] == 1


def test_v2_list_order_remains_significant_for_exact_match(v2_files):
    """Value PR uses sets, while canonical and semantic exact match retain order."""
    prepared = load(v2_files)
    query = "With roses and lilies"
    gold = {name: empty() for name in prepared.cases[0].annotations}
    gold["preferred_flowers"] = {
        "state": "RESOLVED", "unresolved_mentions": [],
        "resolved_values": [
            {"value": value, "evidence": [span(query, query)]} for value in ("Rose", "Lily")
        ],
    }
    case = replace(prepared.cases[0], query=query, annotations=gold, expected={
        "size": (), "budget_max": (), "preferred_flowers": ("Rose", "Lily"), "excluded_flowers": (),
    })
    prepared = replace(prepared, cases=(case,))
    output = deepcopy(gold)
    output["preferred_flowers"]["resolved_values"].reverse()

    class ReversedPrediction:
        def extract(self, query):
            return AnnotationPrediction(output)

    report = evaluate_extractor(prepared, ReversedPrediction())
    field = report["groups"]["all"]["fields"]["preferred_flowers"]
    assert field["canonical_values"]["precision"] == field["canonical_values"]["recall"] == 1
    assert field["canonical_values"]["exact_match_rate"] == 0
    assert field["completeness"]["semantic_exact_match_rate"] == 0


@pytest.mark.parametrize("problem", [
    "absent_with_values", "resolved_with_pending", "partial_without_pending", "pending_without_mentions",
    "scalar_partial", "wrong_order", "null_value", "unknown_flower", "duplicate_value",
    "unknown_reason", "bad_span", "bad_text", "bool_offset", "support_without_mention",
    "duplicate_mention", "out_of_catalog_candidates", "exact_catalog_mention", "unknown_key",
    "conflict_without_conflicting_reason", "conflict_without_alternatives",
])
def test_v2_validation_rejects_inconsistent_annotation_shapes(v2_files, problem):
    prepared = load(v2_files)
    case = prepared.cases[0]
    field = "preferred_flowers"
    output = deepcopy(case.annotations[field])
    expected = case.expected[field]
    if problem == "absent_with_values":
        output["state"] = "ABSENT"
    elif problem == "resolved_with_pending":
        output["state"] = "RESOLVED"
    elif problem == "partial_without_pending":
        output["unresolved_mentions"] = []
    elif problem == "pending_without_mentions":
        output = {"state": "AMBIGUOUS", "resolved_values": [], "unresolved_mentions": []}
        expected = ()
    elif problem == "scalar_partial":
        field = "size"
        output["resolved_values"][0]["value"] = "SMALL"
        output["unresolved_mentions"][0].update(reason="UNDECIDED", candidates=["LARGE"])
        expected = ("SMALL",)
    elif problem == "wrong_order":
        item = deepcopy(output["resolved_values"][0])
        item["value"] = "Lily"
        output["resolved_values"].append(item)
        expected = ("Lily", "Rose")
    elif problem == "null_value":
        output["resolved_values"][0]["value"] = None
    elif problem == "unknown_flower":
        output["resolved_values"][0]["value"] = "Orchid"
    elif problem == "duplicate_value":
        output["resolved_values"].append(deepcopy(output["resolved_values"][0]))
    elif problem == "unknown_reason":
        output["unresolved_mentions"][0]["reason"] = "OTHER"
    elif problem == "bad_span":
        output["unresolved_mentions"][0]["mention"]["end"] = 999
    elif problem == "bad_text":
        output["resolved_values"][0]["evidence"][0]["text"] = "incorrect"
    elif problem == "bool_offset":
        output["resolved_values"][0]["evidence"][0]["start"] = False
    elif problem == "support_without_mention":
        output["unresolved_mentions"][0]["evidence"] = [span(case.query, "Sem antúrios")]
    elif problem == "duplicate_mention":
        output["unresolved_mentions"].append(deepcopy(output["unresolved_mentions"][0]))
    elif problem == "out_of_catalog_candidates":
        output["unresolved_mentions"][0]["candidates"] = ["Rose"]
    elif problem == "exact_catalog_mention":
        output["resolved_values"][0]["evidence"] = [span("Rose", "Rose")]
        output["unresolved_mentions"][0]["mention"] = span("Rose", "Rose")
        output["unresolved_mentions"][0]["evidence"] = [span("Rose", "Rose")]
        with pytest.raises(ValueError, match="canonical name"):
            validate_field_v2("Rose", field, output, prepared.catalog, expected)
        return
    elif problem == "unknown_key":
        output["extra"] = True
    else:
        output["resolved_values"] = []
        output["state"] = "CONFLICT"
        expected = ()
        if problem == "conflict_without_alternatives":
            output["unresolved_mentions"][0].update(reason="CONFLICTING_INFORMATION", candidates=["Rose"])
    with pytest.raises(ValueError):
        validate_field_v2(case.query, field, output, prepared.catalog, expected)


def test_migration_preserves_v1_and_requires_explicit_pending_diagnoses(v2_files):
    """Migration is structural; semantic reasons must come from reviewed decisions."""
    source = {
        "annotation_version": 1, "dataset_sha256": "unchanged", "cases": [{
            "id": "example", "language": "pt", "reviewed": False,
            "fields": {"size": {"state": "AMBIGUOUS", "evidence": []}},
        }],
    }
    original = deepcopy(source)
    with pytest.raises(ValueError, match="Explicit pending"):
        migrate_annotations_v1(source, {})
    q = "Small or large"
    decision = pending(q, q, q, "UNDECIDED", ("SMALL", "LARGE"))
    migrated = migrate_annotations_v1(source, {("example", "size"): [decision]})
    assert source == original
    assert migrated["annotation_version"] == 2
    assert migrated["dataset_sha256"] == source["dataset_sha256"]
    assert migrated["cases"][0]["reviewed"] is False
    assert migrated["cases"][0]["fields"]["size"]["unresolved_mentions"] == [decision]
    with pytest.raises(ValueError, match="unknown"):
        migrate_annotations_v1({**source, "cases": []}, {("unknown", "size"): [decision]})


def test_cli_v2_template_and_version_mismatch(v2_files, tmp_path, monkeypatch):
    """V2 is explicit; v1 remains the default and sidecar versions control scoring."""
    dataset, sidecar = v2_files
    output = tmp_path / "template.json"
    monkeypatch.setattr("sys.argv", [
        "extract", "--dataset", str(dataset), "--prepare-annotations", "--annotation-version", "2",
        "--output", str(output),
    ])
    assert main() == 0
    template = json.loads(output.read_text())
    assert template["annotation_version"] == 2
    assert template["cases"][0]["reviewed"] is False
    assert template["cases"][0]["fields"]["size"]["resolved_values"] == []
    output = tmp_path / "not_created.json"
    monkeypatch.setattr("sys.argv", [
        "extract", "--dataset", str(dataset), "--annotations", str(sidecar),
        "--annotation-version", "1", "--output", str(output),
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert not output.exists()
    monkeypatch.setattr("sys.argv", [
        "extract", "--dataset", str(dataset), "--annotations", str(sidecar),
        "--output", str(output),
    ])
    assert main() == 0
    assert json.loads(output.read_text())["evaluation_version"] == 2
