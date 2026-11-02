"""Versioned canonical-value and pending/completeness scoring; no recognition rules."""

from collections import Counter
from collections.abc import Callable
from statistics import fmean
from typing import Any

from .annotation_v2 import (
    AnnotationPrediction,
    UnresolvedReason,
    canonical_value,
    validate_field_v2,
    validate_span,
)
from .annotations import PreparedEvaluation
from .contracts import FIELDS, RULES_VERSION
from .evaluation import _rate, _scores


def _bucket() -> dict[str, Any]:
    """Initialize one language/field aggregation without shared mutable counters."""
    return {
        "canonical": Counter(dict.fromkeys((
            "cases", "tp", "fp", "fn", "expected_absent_cases",
            "false_positive_cases", "exact_matches",
        ), 0)),
        "pending": Counter(), "completeness": Counter(),
        "expected_states": Counter(), "predicted_states": Counter(),
        "reasons": {reason.value: Counter() for reason in UnresolvedReason},
    }


def _pending_key(mention: dict[str, Any]) -> tuple:
    """Score mention detection by field, reason and original span, not context size."""
    span = mention["mention"]
    return mention["reason"], span["start"], span["end"]


def _semantic_keys(items: list, field: str, catalog) -> set:
    """Exact semantics includes candidate alternatives, compared as a set."""
    return {
        (*_pending_key(item), frozenset(canonical_value(field, c, catalog) for c in item["candidates"]))
        for item in items
    }


def _prediction(extraction, query: str, catalog) -> tuple[dict, bool]:
    """Accept explicit v2 output or project legacy values without inventing diagnostics."""
    if isinstance(extraction, AnnotationPrediction):
        if set(extraction.fields) != set(FIELDS):
            raise ValueError("V2 predictions must contain all four fields.")
        for field, result in extraction.fields.items():
            validate_field_v2(query, field, result, catalog)
        return extraction.fields, True
    fields = {}
    for name, result in extraction.fields().items():
        fields[name] = {
            "state": result.state.value,
            "resolved_values": [
                {"value": item.value, "evidence": [
                    {"start": e.start, "end": e.end, "text": e.text} for e in item.evidence
                ]}
                for item in result.values
            ],
            "unresolved_mentions": [],
        }
    return fields, False


def _mention_counts(predicted: set, expected: set) -> dict[str, int]:
    """Wrong reasons or wrong spans are a false positive plus a false negative."""
    return {
        "tp": len(predicted & expected), "fp": len(predicted - expected),
        "fn": len(expected - predicted), "predicted": len(predicted), "expected": len(expected),
    }


def _pr(counts: Counter) -> dict[str, Any]:
    """Expose explicit zero denominators for a diagnostic class with no mentions."""
    tp, fp, fn = (counts.get(key, 0) for key in ("tp", "fp", "fn"))
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "predicted": counts.get("predicted", 0), "expected": counts.get("expected", 0),
        "precision": _rate(tp, tp + fp), "recall": _rate(tp, tp + fn),
        "f1": _rate(2 * tp, 2 * tp + fp + fn),
    }


def _summarize(bucket: dict[str, Any]) -> dict[str, Any]:
    """Keep canonical accuracy separate from complete interpretation and coverage."""
    completeness = bucket["completeness"]
    canonical_scores = _scores(dict(bucket["canonical"]))
    canonical_scores.pop("state_accuracy")
    return {
        "canonical_values": canonical_scores,
        "pending_mentions": {
            "all": _pr(bucket["pending"]),
            "by_reason": {reason: _pr(counts) for reason, counts in bucket["reasons"].items()},
        },
        "completeness": {
            **dict(completeness),
            "state_accuracy": _rate(completeness["state_correct"], completeness["field_cases"]),
            "semantic_exact_match_rate": _rate(completeness["semantic_exact"], completeness["field_cases"]),
            "value_field_coverage": _rate(completeness["value_fields_attempted"], completeness["expected_value_fields"]),
            "claimed_complete_field_rate": _rate(completeness["claimed_complete_fields"], completeness["field_cases"]),
            "expected_states": dict(bucket["expected_states"]),
            "predicted_states": dict(bucket["predicted_states"]),
        },
    }


def _evidence_counts(query: str, field: str, predicted: dict, gold: dict, catalog) -> Counter:
    """Span alignment is diagnostic, not an automatic semantic faithfulness proof."""
    counts = Counter()
    for item in predicted["resolved_values"]:
        counts["confirmed_values"] += 1
        aligned = False
        for span in item["evidence"]:
            counts["spans"] += 1
            try:
                validate_span(query, span)
            except ValueError:
                continue
            counts["valid_spans"] += 1
            for expected in gold["resolved_values"]:
                if canonical_value(field, item["value"], catalog) == canonical_value(field, expected["value"], catalog):
                    aligned |= any(span["start"] <= e["start"] < e["end"] <= span["end"] for e in expected["evidence"])
        counts["gold_span_aligned_values"] += aligned
    for pending in predicted["unresolved_mentions"]:
        for span in (pending["mention"], *pending["evidence"]):
            counts["spans"] += 1
            validate_span(query, span)
            counts["valid_spans"] += 1
    return counts


def evaluate_v2(prepared: PreparedEvaluation, extractor, clock: Callable[[], float]) -> dict[str, Any]:
    """Measure missing legacy diagnostics as FN, never supply them from gold."""
    buckets = {
        language: {name: _bucket() for name in (*FIELDS, "all_fields")}
        for language in ("all", "pt", "en")
    }
    evidence_counts = Counter()
    cases = []
    for case in prepared.cases:
        started = clock()
        extraction = extractor.extract(case.query)
        elapsed = clock() - started
        prediction, structured = _prediction(extraction, case.query, prepared.catalog)
        canonical_matches, semantic_matches = {}, {}
        for name in FIELDS:
            gold, actual = case.annotations[name], prediction[name]
            values = tuple(canonical_value(name, v["value"], prepared.catalog) for v in actual["resolved_values"])
            expected = case.expected[name]
            predicted_keys = {_pending_key(item) for item in actual["unresolved_mentions"]}
            expected_keys = {_pending_key(item) for item in gold["unresolved_mentions"]}
            span_counts = _evidence_counts(case.query, name, actual, gold, prepared.catalog)
            evidence_counts.update(span_counts)
            canonical_matches[name] = values == expected
            semantic_matches[name] = (
                values == expected and actual["state"] == gold["state"]
                and _semantic_keys(actual["unresolved_mentions"], name, prepared.catalog)
                == _semantic_keys(gold["unresolved_mentions"], name, prepared.catalog)
                and span_counts["spans"] == span_counts["valid_spans"]
            )
            for language in ("all", case.language):
                for key in (name, "all_fields"):
                    bucket = buckets[language][key]
                    bucket["canonical"].update({
                        "cases": 1, "tp": len(set(values) & set(expected)),
                        "fp": len(set(values) - set(expected)), "fn": len(set(expected) - set(values)),
                        "expected_absent_cases": int(not expected),
                        "false_positive_cases": int(not expected and bool(values)),
                        "exact_matches": int(canonical_matches[name]),
                    })
                    bucket["pending"].update(_mention_counts(predicted_keys, expected_keys))
                    for reason in UnresolvedReason:
                        bucket["reasons"][reason.value].update(_mention_counts(
                            {k for k in predicted_keys if k[0] == reason.value},
                            {k for k in expected_keys if k[0] == reason.value},
                        ))
                    bucket["completeness"].update({
                        "field_cases": 1, "state_correct": int(actual["state"] == gold["state"]),
                        "semantic_exact": int(semantic_matches[name]),
                        "expected_value_fields": int(bool(expected)),
                        "value_fields_attempted": int(bool(expected) and bool(values)),
                        "fields_with_values": int(bool(values)),
                        "claimed_complete_fields": int(actual["state"] in {"ABSENT", "RESOLVED"}),
                        "correctly_complete_fields": int(gold["state"] in {"ABSENT", "RESOLVED"} and semantic_matches[name]),
                    })
                    bucket["expected_states"][gold["state"]] += 1
                    bucket["predicted_states"][actual["state"]] += 1
        cases.append({
            "id": case.id, "language": case.language,
            "prediction_contract": "v2" if structured else "legacy",
            "pending_mentions_supported": structured,
            "expected": case.annotations,
            "actual": extraction.to_dict(),
            "canonical_field_matches": canonical_matches,
            "semantic_field_matches": semantic_matches,
            "canonical_exact_match": all(canonical_matches.values()),
            "semantic_exact_match": all(semantic_matches.values()),
            "extraction_seconds": elapsed,
        })
    groups = {}
    for language, fields in buckets.items():
        selected = [case for case in cases if language == "all" or case["language"] == language]
        groups[language] = {
            "cases": len(selected),
            "all_fields": _summarize(fields["all_fields"]),
            "fields": {name: _summarize(fields[name]) for name in FIELDS},
        }
        for kind in ("canonical", "semantic"):
            count = sum(case[f"{kind}_exact_match"] for case in selected)
            groups[language][f"{kind}_exact_match"] = {
                "correct": count, "total": len(selected), "rate": _rate(count, len(selected)),
            }
    times = [case["extraction_seconds"] for case in cases]
    return {
        "experiment": RULES_VERSION, "evaluation_version": 2, "annotation_version": 2,
        "dataset_version": prepared.dataset_version, "dataset_sha256": prepared.dataset_sha256,
        "groups": groups,
        "evidence": {
            **dict(evidence_counts),
            "span_integrity": _rate(evidence_counts["valid_spans"], evidence_counts["spans"]),
            "gold_span_alignment_rate": _rate(evidence_counts["gold_span_aligned_values"], evidence_counts["confirmed_values"]),
            "semantic_review_required": True,
        },
        "timing": {"total_extraction_seconds": sum(times), "mean_extraction_seconds": fmean(times) if times else None},
        "experimental_targets": {"precision": 0.95, "recall": 0.80, "acceptance_gate": False},
        "legacy_prediction_cases": sum(not case["pending_mentions_supported"] for case in cases),
        "cases": cases,
    }
