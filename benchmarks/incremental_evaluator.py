"""Compare full-closure and dependency-indexed native evaluation on one revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmarks.common import Environment, TimingSummary, environment, project_root, summarize
from benchmarks.multi_application_workload import native_workload
from research.native_backend import NativeSolver, NativeWorkMetrics


@dataclass(frozen=True, slots=True)
class EvaluatorMeasurement:
    """Timing, model, and deterministic work evidence for one evaluator mode."""

    solve: TimingSummary
    total: TimingSummary
    model_count: int
    models_sha256: str
    work: NativeWorkMetrics


@dataclass(frozen=True, slots=True)
class IncrementalEvaluatorCase:
    """Full and dependency-indexed results for one candidate-domain size."""

    candidate_values: int
    full_closure: EvaluatorMeasurement
    dependency_indexed: EvaluatorMeasurement
    visible_models_equal: bool
    rule_body_evaluation_reduction: int


@dataclass(frozen=True, slots=True)
class IncrementalEvaluatorRun:
    """Machine-readable same-revision evaluator comparison."""

    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[IncrementalEvaluatorCase, ...]


def _digest(models: tuple[tuple[str, ...], ...]) -> str:
    canonical = "\n".join(" ".join(model) for model in models).encode()
    return hashlib.sha256(canonical).hexdigest()


def _measure(
    candidate_values: int,
    *,
    dependency_indexed: bool,
    repeats: int,
    warmups: int,
) -> tuple[EvaluatorMeasurement, tuple[tuple[str, ...], ...]]:
    solve_samples: list[float] = []
    total_samples: list[float] = []
    expected_models: tuple[tuple[str, ...], ...] | None = None
    expected_work: NativeWorkMetrics | None = None
    for index in range(warmups + repeats):
        started = time.perf_counter()
        result = NativeSolver().solve(
            native_workload(candidate_values),
            dependency_indexed_evaluation=dependency_indexed,
        )
        total = time.perf_counter() - started
        models = tuple(model.visible for model in result.models)
        if expected_models is None:
            expected_models = models
            expected_work = result.work_metrics
        elif models != expected_models or result.work_metrics != expected_work:
            raise RuntimeError("native evaluator measurement changed between repeated runs")
        if index >= warmups:
            solve_samples.append(result.solve_seconds)
            total_samples.append(total)
    if expected_models is None or expected_work is None:
        raise RuntimeError("native evaluator measurement produced no observations")
    return (
        EvaluatorMeasurement(
            solve=summarize(solve_samples),
            total=summarize(total_samples),
            model_count=len(expected_models),
            models_sha256=_digest(expected_models),
            work=expected_work,
        ),
        expected_models,
    )


def run_comparison(
    sizes: tuple[int, ...],
    *,
    repeats: int,
    warmups: int = 1,
) -> IncrementalEvaluatorRun:
    """Measure both evaluators and require complete normalized-model equality."""

    cases: list[IncrementalEvaluatorCase] = []
    for size in sizes:
        full, full_models = _measure(
            size,
            dependency_indexed=False,
            repeats=repeats,
            warmups=warmups,
        )
        incremental, incremental_models = _measure(
            size,
            dependency_indexed=True,
            repeats=repeats,
            warmups=warmups,
        )
        if full_models != incremental_models:
            raise RuntimeError("dependency-indexed models differ from full closure")
        cases.append(
            IncrementalEvaluatorCase(
                candidate_values=size,
                full_closure=full,
                dependency_indexed=incremental,
                visible_models_equal=True,
                rule_body_evaluation_reduction=(
                    full.work.rule_body_evaluations - incremental.work.rule_body_evaluations
                ),
            )
        )
    return IncrementalEvaluatorRun(
        schema_version=1,
        family="native-full-vs-dependency-indexed-evaluation",
        repeats=repeats,
        warmups=warmups,
        environment=environment(project_root()),
        cases=tuple(cases),
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 100, 1000])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if any(size < 1 for size in arguments.sizes):
        parser.error("every candidate-domain size must be positive")
    if arguments.repeats < 1 or arguments.warmups < 0:
        parser.error("repeats must be positive and warmups must not be negative")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    result = run_comparison(
        tuple(arguments.sizes),
        repeats=arguments.repeats,
        warmups=arguments.warmups,
    )
    rendered = json.dumps(asdict(result), indent=2) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
