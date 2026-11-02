"""Evaluation metric checks with a fake interpreter; no Ollama calls."""

import json
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.services.llm_provider import LLMProviderError
from evaluation.bouquet_interpreter import (
    DATASET_PATHS,
    EvaluationDataset,
    evaluate_dataset,
    load_dataset,
    main,
)


class FakeInterpreter:
    """Return predetermined interpretations or failures for named inputs."""

    def __init__(
        self,
        outcomes: dict[str, BouquetInterpretation | Exception],
        metrics: dict[str, int | float | None] | None = None,
    ) -> None:
        self.outcomes = outcomes
        if metrics is not None:
            self.provider = SimpleNamespace(last_inference_metrics=metrics)

    def interpret(self, text: str) -> BouquetInterpretation:
        """Return the recorded result without network or database access."""
        outcome = self.outcomes[text]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def half_second_clock(count: int) -> Iterator[float]:
    """Supply deterministic start/end readings for each case."""
    return iter(index / 2 for index in range(count * 2))


def test_versioned_dataset_covers_absence_and_both_languages():
    """The fixture keeps the original request and multiple missing-size cases."""
    dataset = load_dataset()
    assert len(dataset.cases) == 16
    original = next(
        case for case in dataset.cases if case.id == "romantic_red_birthday"
    )
    assert original.input == (
        "I want a romantic red bouquet with roses for a birthday, up to R$150."
    )
    assert original.expected.size is None
    assert original.expected.budget_max == 150
    assert sum(case.expected.size is None for case in dataset.cases) >= 8
    assert any("buquê" in case.input.lower() for case in dataset.cases)
    assert any(case.expected.excluded_flowers for case in dataset.cases)
    assert any(case.expected.budget_max is None for case in dataset.cases)


def test_perfect_fake_interpreter_gets_full_credit():
    """A fully matching interpreter scores every field and readiness correctly."""
    dataset = load_dataset()
    outcomes = {case.input: case.expected for case in dataset.cases}
    clock = half_second_clock(len(dataset.cases))
    report = evaluate_dataset(
        FakeInterpreter(outcomes), dataset, clock=lambda: next(clock)
    )

    assert report["exact_match"] == {"correct": 16, "total": 16, "rate": 1.0}
    assert all(field["rate"] == 1.0 for field in report["field_accuracy"].values())
    assert report["invented_values"]["count"] == 0
    assert report["invented_values"]["rate"] == 0.0
    assert report["readiness"]["correct"] == 16
    assert report["readiness"]["by_status"]["READY"]["correct"] > 0
    assert report["readiness"]["by_status"]["NEEDS_CLARIFICATION"]["correct"] > 0
    assert report["mean_latency_seconds"] == 0.5
    assert report["total_latency_seconds"] == 8.0
    assert report["cases_failed"] == 0


def test_inference_telemetry_is_saved_per_case_and_aggregated():
    """Ollama metrics are captured without changing interpretation scores."""
    dataset = load_dataset()
    selected = EvaluationDataset(
        version=1, catalog=dataset.catalog, cases=dataset.cases[:2]
    )
    metrics = {
        "total_duration": 1000,
        "load_duration": 100,
        "prompt_eval_duration": 200,
        "eval_duration": 500,
        "prompt_eval_count": 20,
        "eval_count": 4,
        "eval_tokens_per_second": 8_000_000,
    }
    clock = half_second_clock(2)
    report = evaluate_dataset(
        FakeInterpreter(
            {case.input: case.expected for case in selected.cases}, metrics=metrics
        ),
        selected,
        clock=lambda: next(clock),
    )

    assert report["exact_match"]["correct"] == 2
    assert [case["ollama_metrics"] for case in report["cases"]] == [metrics, metrics]
    assert report["ollama_inference_metrics"] == {
        "responses_with_metrics": 2,
        "totals": {
            "total_duration": 2000,
            "load_duration": 200,
            "prompt_eval_duration": 400,
            "eval_duration": 1000,
            "prompt_eval_count": 40,
            "eval_count": 8,
        },
        "responses_by_metric": dict.fromkeys(metrics.keys() - {"eval_tokens_per_second"}, 2),
        "eval_tokens_per_second": 8_000_000,
    }


def test_invented_size_changes_readiness_without_hiding_failure():
    """A guessed size counts as one hallucination and a wrong READY result."""
    dataset = load_dataset()
    original = next(
        case for case in dataset.cases if case.id == "romantic_red_birthday"
    )
    one_case = EvaluationDataset(
        version=1, catalog=dataset.catalog, cases=[original]
    )
    invented = BouquetInterpretation.model_validate({
        **original.expected.model_dump(), "size": "MEDIUM",
    })
    clock = half_second_clock(1)
    report = evaluate_dataset(
        FakeInterpreter({original.input: invented}),
        one_case,
        clock=lambda: next(clock),
    )

    assert report["exact_match"]["rate"] == 0.0
    assert report["field_accuracy"]["size"]["rate"] == 0.0
    assert report["field_accuracy"]["occasion"]["rate"] == 1.0
    assert report["invented_values"] == {
        "count": 1, "evaluated_absent_fields": 2, "rate": 0.5,
    }
    assert report["readiness"]["correct"] == 0
    assert report["readiness"]["by_status"]["READY"]["actual"] == 1
    assert report["cases"][0]["expected_status"] == "NEEDS_CLARIFICATION"
    assert report["cases"][0]["actual_status"] == "READY"


def test_provider_error_is_recorded_and_next_case_runs():
    """An unavailable result is not silently counted as an absent value."""
    dataset = load_dataset()
    selected = EvaluationDataset(
        version=1, catalog=dataset.catalog, cases=dataset.cases[:2]
    )
    first, second = selected.cases
    clock = half_second_clock(2)
    report = evaluate_dataset(
        FakeInterpreter({
            first.input: LLMProviderError("unavailable"),
            second.input: second.expected,
        }),
        selected,
        clock=lambda: next(clock),
    )

    assert report["cases_failed"] == 1
    assert report["cases_completed"] == 1
    assert report["cases"][0]["actual"] is None
    assert report["cases"][0]["actual_status"] is None
    assert report["cases"][0]["error"] == "LLMProviderError: unavailable"
    assert report["cases"][1]["exact_match"] is True
    assert report["exact_match"]["rate"] == 0.5
    assert report["mean_latency_seconds"] == 0.5


@pytest.mark.parametrize("field,value", [
    ("occasion", "Invented"),
    ("preferred_flowers", ["Invented"]),
])
def test_dataset_rejects_expected_values_outside_snapshot(field, value):
    """Labels must use the versioned catalog rather than arbitrary names."""
    payload = load_dataset().model_dump(mode="json")
    payload["cases"][0]["expected"][field] = value
    with pytest.raises(ValidationError, match="Invalid catalog value"):
        EvaluationDataset.model_validate(payload)


def test_dataset_requires_explicit_nulls():
    """A missing label must not quietly turn into a valid null expectation."""
    payload = load_dataset().model_dump(mode="json")
    del payload["cases"][0]["expected"]["size"]
    with pytest.raises(ValidationError, match="specify every field"):
        EvaluationDataset.model_validate(payload)


def test_v2_has_new_cases_and_preserves_catalog():
    """The optimization dataset expands coverage without reusing v1 inputs."""
    original = load_dataset()
    dataset = load_dataset(DATASET_PATHS[2])
    assert dataset.version == 2
    assert len(dataset.cases) == 30
    assert dataset.catalog == original.catalog
    assert not {case.id for case in dataset.cases} & {case.id for case in original.cases}
    assert not {case.input.casefold() for case in dataset.cases} & {
        case.input.casefold() for case in original.cases
    }
    assert sum(case.id.startswith("pt_") for case in dataset.cases) == 15
    assert sum(case.id.startswith("en_") for case in dataset.cases) == 15
    assert sum(case.expected_status.value == "READY" for case in dataset.cases) == 10
    assert sum(case.expected.size is None for case in dataset.cases) == 15


@pytest.mark.parametrize("status", [None, "READY", "UNKNOWN"])
def test_v2_rejects_missing_invalid_or_inconsistent_status(status):
    """Readiness labels are mandatory and must agree with interpretation fields."""
    payload = load_dataset(DATASET_PATHS[2]).model_dump(mode="json")
    incomplete = next(case for case in payload["cases"] if case["expected"]["size"] is None)
    if status is None:
        del incomplete["expected_status"]
    else:
        incomplete["expected_status"] = status
    with pytest.raises(ValidationError):
        EvaluationDataset.model_validate(payload)


@pytest.mark.parametrize("version", [0, 3])
def test_dataset_rejects_unsupported_versions(version):
    """Unrecognized versions cannot silently use an existing contract."""
    payload = load_dataset().model_dump(mode="json")
    payload["version"] = version
    with pytest.raises(ValidationError, match="Unsupported"):
        EvaluationDataset.model_validate(payload)


@pytest.mark.parametrize("field", ["id", "input"])
def test_dataset_rejects_duplicate_cases(field):
    """Duplicate requests or IDs would distort the aggregate metrics."""
    payload = load_dataset(DATASET_PATHS[2]).model_dump(mode="json")
    payload["cases"][1][field] = payload["cases"][0][field]
    with pytest.raises(ValidationError, match="unique"):
        EvaluationDataset.model_validate(payload)


def test_v2_perfect_fake_interpreter_preserves_metrics_and_status_labels():
    """Run all new cases deterministically without a model or provider call."""
    dataset = load_dataset(DATASET_PATHS[2])
    clock = half_second_clock(30)
    report = evaluate_dataset(
        FakeInterpreter({case.input: case.expected for case in dataset.cases}),
        dataset, clock=lambda: next(clock),
    )
    assert report["dataset_version"] == 2
    assert report["cases_completed"] == 30
    assert report["cases_failed"] == 0
    assert report["exact_match"] == {"correct": 30, "total": 30, "rate": 1.0}
    assert all(field["rate"] == 1.0 for field in report["field_accuracy"].values())
    assert report["invented_values"]["count"] == 0
    assert report["readiness"]["rate"] == 1.0
    assert [case["expected_status"] for case in report["cases"]] == [
        case.expected_status.value for case in dataset.cases
    ]


@pytest.mark.parametrize("constrained", [False, True])
@pytest.mark.parametrize("selection,version", [
    ([], 1),
    (["--dataset-version", "1"], 1),
    (["--dataset-version", "2"], 2),
    (["--dataset", str(DATASET_PATHS[2])], 2),
])
def test_cli_selects_dataset_without_model_calls(
    monkeypatch, tmp_path, selection, version, constrained,
):
    """The CLI selects bundled versions or custom paths independently of providers."""
    from evaluation import bouquet_interpreter as runner

    output = tmp_path / "report.json"
    arguments = [
        "evaluate", *selection, "--model", "fake-model", "--output", str(output),
    ]
    if constrained:
        arguments.append("--catalog-constrained-output")
    monkeypatch.setattr("sys.argv", arguments)
    monkeypatch.delenv("OLLAMA_THINK", raising=False)
    monkeypatch.setattr(runner, "OllamaProvider", lambda config: None)

    def make_interpreter(provider, catalog, **kwargs):
        assert kwargs == ({"catalog_constraints": True} if constrained else {})
        dataset = load_dataset(DATASET_PATHS[version])
        assert catalog == dataset.catalog
        return FakeInterpreter({case.input: case.expected for case in dataset.cases})

    monkeypatch.setattr(runner, "LLMBouquetRequestInterpreter", make_interpreter)
    assert main() == 0
    report = json.loads(output.read_text())
    assert report["dataset_version"] == version
    assert report["cases_total"] == (16 if version == 1 else 30)
    assert report["exact_match"]["rate"] == 1.0
    assert report["configuration"]["catalog_constrained_output"] is constrained
    assert report["configuration"]["catalog_constraint_version"] == (1 if constrained else None)


def test_list_order_still_counts_as_a_field_error():
    """Generation constraints must not hide reversed lists in evaluation."""
    dataset = load_dataset(DATASET_PATHS[2])
    case = next(case for case in dataset.cases if len(case.expected.colors or []) == 2)
    selected = EvaluationDataset(version=2, catalog=dataset.catalog, cases=[case])
    actual = case.expected.model_copy(update={"colors": list(reversed(case.expected.colors))})
    report = evaluate_dataset(FakeInterpreter({case.input: actual}), selected)
    assert report["exact_match"]["rate"] == 0
    assert report["field_accuracy"]["colors"]["rate"] == 0


@pytest.mark.parametrize("selection", [
    ["--dataset-version", "3"],
    ["--dataset-version", "2", "--dataset", str(DATASET_PATHS[1])],
])
def test_cli_rejects_invalid_or_conflicting_selection(monkeypatch, selection):
    """Invalid dataset selection fails before creating any provider."""
    monkeypatch.setattr("sys.argv", ["evaluate", *selection])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
