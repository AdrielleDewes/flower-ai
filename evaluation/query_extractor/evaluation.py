"""Standalone value/state scoring, intentionally separate from LLM metrics."""

from collections import Counter
from collections.abc import Callable
from statistics import fmean
from time import perf_counter
from typing import Any

from .annotations import PreparedEvaluation, field_values
from .contracts import FIELDS, RULES_VERSION, ExtractionState
from .extractor import QueryExtractor


def _rate(numerator: int, denominator: int) -> float | None:
    """Keep undefined scores explicit, never treating no predictions as precision 1."""
    return numerator / denominator if denominator else None


def _scores(counts: dict[str, int]) -> dict[str, Any]:
    """Compute micro value metrics with abstentions left in recall denominators."""
    tp, fp, fn = (counts.get(name, 0) for name in ("tp", "fp", "fn"))
    return {
        **counts,
        "precision": _rate(tp, tp + fp),
        "recall": _rate(tp, tp + fn),
        "f1": _rate(2 * tp, 2 * tp + fp + fn),
        "false_positive_case_rate": _rate(
            counts.get("false_positive_cases", 0), counts.get("expected_absent_cases", 0),
        ),
        "exact_match_rate": _rate(counts.get("exact_matches", 0), counts.get("cases", 0)),
        "state_accuracy": _rate(counts.get("state_correct", 0), counts.get("cases", 0)),
    }


def evaluate_extractor(
    prepared: PreparedEvaluation,
    extractor: QueryExtractor,
    clock: Callable[[], float] = perf_counter,
) -> dict[str, Any]:
    """Score confirmed values only; never fill other interpretation fields with gold."""
    if prepared.annotation_version == 2:
        from .evaluation_v2 import evaluate_v2

        return evaluate_v2(prepared, extractor, clock)
    counters: dict[str, dict[str, Counter]] = {
        language: {field: Counter() for field in FIELDS}
        for language in ("all", "pt", "en")
    }
    results = []
    evidence_total = evidence_valid = support_aligned = value_total = 0
    for case in prepared.cases:
        start = clock()
        extraction = extractor.extract(case.query)
        elapsed = clock() - start
        matches = {}
        for name, result in extraction.fields().items():
            actual = tuple(value.value for value in result.values)
            expected = case.expected[name]
            actual_set, expected_set = set(actual), set(expected)
            expected_state = case.annotations[name]["state"]
            exact = actual == expected and result.state.value == expected_state
            matches[name] = exact
            for language in ("all", case.language):
                counts = counters[language][name]
                counts.update({
                    "cases": 1,
                    "tp": len(actual_set & expected_set),
                    "fp": len(actual_set - expected_set),
                    "fn": len(expected_set - actual_set),
                    "expected_absent_cases": int(not expected),
                    "false_positive_cases": int(not expected and bool(actual)),
                    "exact_matches": int(exact),
                    "state_correct": int(result.state.value == expected_state),
                    "resolved_fields": int(result.state is ExtractionState.RESOLVED),
                    "absent_fields": int(result.state is ExtractionState.ABSENT),
                    "ambiguous_fields": int(result.state is ExtractionState.AMBIGUOUS),
                    "conflict_fields": int(result.state is ExtractionState.CONFLICT),
                })
            for value in result.values:
                value_total += 1
                aligned = False
                for evidence in value.evidence:
                    evidence_total += 1
                    valid = (
                        0 <= evidence.start < evidence.end <= len(case.query)
                        and case.query[evidence.start:evidence.end] == evidence.text
                    )
                    evidence_valid += valid
                    for gold in case.annotations[name]["evidence"]:
                        raw = gold.get("value")
                        if raw is None:
                            continue
                        gold_values = field_values(name, raw if name in {"size", "budget_max"} else [raw])
                        aligned |= (
                            valid and value.value in gold_values
                            and evidence.start <= gold["start"] < gold["end"] <= evidence.end
                        )
                support_aligned += aligned
        results.append({
            "id": case.id, "language": case.language,
            "actual": extraction.to_dict(),
            "expected": {
                name: [str(value) for value in expected]
                for name, expected in case.expected.items()
            },
            "expected_states": {
                name: annotation["state"] for name, annotation in case.annotations.items()
            },
            "field_matches": matches,
            "exact_match": all(matches.values()),
            "extraction_seconds": elapsed,
        })
    groups = {}
    for language, fields in counters.items():
        aggregate = Counter()
        for counts in fields.values():
            aggregate.update(counts)
        selected = [case for case in results if language == "all" or case["language"] == language]
        groups[language] = {
            "cases": len(selected),
            "micro_values": _scores(dict(aggregate)),
            "fields": {name: _scores(dict(counts)) for name, counts in fields.items()},
            "exact_match": {
                "correct": sum(case["exact_match"] for case in selected),
                "total": len(selected),
                "rate": _rate(sum(case["exact_match"] for case in selected), len(selected)),
            },
        }
    times = [case["extraction_seconds"] for case in results]
    return {
        "experiment": RULES_VERSION,
        "dataset_version": prepared.dataset_version,
        "dataset_sha256": prepared.dataset_sha256,
        "groups": groups,
        "evidence": {
            "spans": evidence_total, "valid_spans": evidence_valid,
            "span_integrity": _rate(evidence_valid, evidence_total),
            "confirmed_values": value_total, "gold_span_aligned_values": support_aligned,
            "gold_span_alignment_rate": _rate(support_aligned, value_total),
            "semantic_review_required": True,
        },
        "timing": {
            "total_extraction_seconds": sum(times),
            "mean_extraction_seconds": fmean(times) if times else None,
        },
        "experimental_targets": {"precision": 0.95, "recall": 0.80, "acceptance_gate": False},
        "cases": results,
    }
