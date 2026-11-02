"""Annotation and metric checks using synthetic fixtures, not the real benchmark."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from evaluation.query_extractor import QueryExtractor
from evaluation.query_extractor.__main__ import main
from evaluation.query_extractor.annotations import (
    annotation_template,
    load_annotated_dataset,
)
from evaluation.query_extractor.evaluation import evaluate_extractor


def write_json(path, data):
    """Write a synthetic fixture without touching tracked datasets."""
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def annotated_files(tmp_path):
    """Manually annotate two simple bilingual queries plus an undecided size."""
    dataset = {
        "version": 2, "catalog": {"flowers": ["Rose", "Lily"]},
        "cases": [
            {
                "id": "synthetic_pt", "input": "Com rosas, sem lírios",
                "expected": {"size": None, "budget_max": None,
                             "preferred_flowers": ["Rose"], "excluded_flowers": ["Lily"]},
            },
            {
                "id": "synthetic_en", "input": "A small bouquet. Budget up to R$25",
                "expected": {"size": "SMALL", "budget_max": "25",
                             "preferred_flowers": None, "excluded_flowers": None},
            },
            {
                "id": "synthetic_unclear", "input": "Small or large bouquet",
                "expected": {"size": None, "budget_max": None,
                             "preferred_flowers": None, "excluded_flowers": None},
            },
        ],
    }
    path = tmp_path / "dataset.json"
    annotations_path = tmp_path / "annotations.json"
    write_json(path, dataset)
    annotations = annotation_template(path)
    labels = [
        {"preferred_flowers": ("Rose", "Com rosas"), "excluded_flowers": ("Lily", "sem lírios")},
        {"size": ("SMALL", "A small bouquet"), "budget_max": ("25", "Budget up to R$25")},
        {},
    ]
    for case, annotation, fields in zip(dataset["cases"], annotations["cases"], labels, strict=True):
        annotation.update(reviewed=True, language="pt" if case["id"] == "synthetic_pt" else "en")
        for field, entry in annotation["fields"].items():
            entry["state"] = "RESOLVED" if field in fields else "ABSENT"
            if field in fields:
                value, text = fields[field]
                start = case["input"].index(text)
                entry["evidence"] = [{"value": value, "text": text, "start": start, "end": start + len(text)}]
        if case["id"] == "synthetic_unclear":
            annotation["fields"]["size"] = {
                "state": "AMBIGUOUS", "evidence": [
                    {"value": None, "text": case["input"], "start": 0, "end": len(case["input"])},
                ],
            }
    write_json(annotations_path, annotations)
    return path, annotations_path


def test_unreviewed_template_is_not_evaluation_ready(annotated_files):
    """Template generation never guesses language, states or semantic evidence."""
    path, annotations_path = annotated_files
    template = annotation_template(path)
    assert all(not case["reviewed"] and case["language"] is None for case in template["cases"])
    write_json(annotations_path, template)
    with pytest.raises(ValueError, match="review"):
        load_annotated_dataset(path, annotations_path)


@pytest.mark.parametrize("problem", [
    "hash", "duplicate", "missing", "review", "language", "span", "text", "state", "value",
])
def test_invalid_annotations_fail_before_extraction(annotated_files, problem):
    """Labels require review, complete IDs and evidence consistent with source text."""
    path, annotations_path = annotated_files
    data = json.loads(annotations_path.read_text())
    first = data["cases"][0]
    flower = first["fields"]["preferred_flowers"]
    if problem == "hash":
        data["dataset_sha256"] = "wrong"
    elif problem == "duplicate":
        data["cases"].append(first)
    elif problem == "missing":
        data["cases"].pop()
    elif problem == "review":
        first["reviewed"] = False
    elif problem == "language":
        first["language"] = "guess"
    elif problem == "span":
        flower["evidence"][0]["end"] = 10000
    elif problem == "text":
        flower["evidence"][0]["text"] = "rosas"
    elif problem == "state":
        flower["state"] = "ABSENT"
    else:
        flower["evidence"][0]["value"] = "Lily"
    write_json(annotations_path, data)
    with pytest.raises(ValueError):
        load_annotated_dataset(path, annotations_path)


def test_standalone_metrics_include_states_evidence_and_languages(annotated_files):
    """Tiny fixtures verify scoring independently of any model or production schema."""
    path, annotations_path = annotated_files
    prepared = load_annotated_dataset(path, annotations_path)
    readings = iter([0, 0.1, 1, 1.1, 2, 2.1])
    report = evaluate_extractor(prepared, QueryExtractor(prepared.catalog), clock=lambda: next(readings))
    assert report["groups"]["all"]["exact_match"] == {"correct": 3, "total": 3, "rate": 1.0}
    assert report["groups"]["all"]["micro_values"]["precision"] == 1
    assert report["groups"]["all"]["micro_values"]["recall"] == 1
    assert report["groups"]["pt"]["cases"] == 1
    assert report["groups"]["en"]["cases"] == 2
    assert report["groups"]["all"]["fields"]["size"]["ambiguous_fields"] == 1
    assert report["evidence"]["span_integrity"] == 1
    assert report["evidence"]["gold_span_alignment_rate"] == 1
    assert report["evidence"]["semantic_review_required"] is True
    assert report["timing"]["mean_extraction_seconds"] == pytest.approx(0.1)
    assert report["experimental_targets"]["acceptance_gate"] is False
    assert prepared.annotation_version == 1
    assert "evaluation_version" not in report
    assert "readiness" not in report


def test_false_positive_wrong_value_and_abstention_denominators(annotated_files):
    """A wrong value counts FP+FN, and abstention never disappears from recall."""
    path, annotations_path = annotated_files
    prepared = load_annotated_dataset(path, annotations_path)

    class WrongExtractor:
        def extract(self, query):
            return QueryExtractor(prepared.catalog).extract("With lilies")

    report = evaluate_extractor(prepared, WrongExtractor())
    field = report["groups"]["pt"]["fields"]["preferred_flowers"]
    assert (field["tp"], field["fp"], field["fn"]) == (0, 1, 1)
    assert field["precision"] == field["recall"] == 0
    budget = report["groups"]["en"]["fields"]["budget_max"]
    assert budget["precision"] is None
    assert budget["recall"] == 0
    en_flowers = report["groups"]["en"]["fields"]["preferred_flowers"]
    assert en_flowers["false_positive_cases"] == 2
    assert en_flowers["expected_absent_cases"] == 2
    assert en_flowers["false_positive_case_rate"] == 1
    assert report["evidence"]["span_integrity"] < 1


def test_ordered_exact_match_differs_from_value_recall(annotated_files):
    """Standalone list scoring documents sets for PR and sequences for exact match."""
    path, annotations_path = annotated_files
    prepared = load_annotated_dataset(path, annotations_path)
    case = prepared.cases[0]
    case = replace(case, query="With roses and lilies", expected={
        **case.expected, "preferred_flowers": ("Lily", "Rose"), "excluded_flowers": (),
    }, annotations={
        **case.annotations,
        "preferred_flowers": {"state": "RESOLVED", "evidence": []},
        "excluded_flowers": {"state": "ABSENT", "evidence": []},
    })
    prepared = replace(prepared, cases=(case,))
    report = evaluate_extractor(prepared, QueryExtractor(prepared.catalog))
    flowers = report["groups"]["all"]["fields"]["preferred_flowers"]
    assert flowers["precision"] == flowers["recall"] == 1
    assert flowers["exact_match_rate"] == 0


def test_cli_preparation_evaluation_and_no_overwrite(monkeypatch, tmp_path, annotated_files):
    """CLI tests operate only on the small synthetic fixture and temporary outputs."""
    dataset, annotations = annotated_files
    output = tmp_path / "template.json"
    monkeypatch.setattr("sys.argv", ["extract", "--dataset", str(dataset), "--prepare-annotations", "--output", str(output)])
    assert main() == 0
    assert json.loads(output.read_text())["cases"][0]["reviewed"] is False
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    output = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["extract", "--dataset", str(dataset), "--annotations", str(annotations), "--output", str(output)])
    assert main() == 0
    report = json.loads(output.read_text())
    assert report["groups"]["all"]["cases"] == 3
    assert "vocabulary_setup_seconds" in report["timing"]
    assert report["annotations_sha256"]


def test_annotation_hash_detects_dataset_change(annotated_files):
    """Even a byte-level change requires explicit re-review, not silent reuse."""
    path, annotations = annotated_files
    with Path(path).open("a") as output:
        output.write("\n")
    with pytest.raises(ValueError, match="hash"):
        load_annotated_dataset(path, annotations)
