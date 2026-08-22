"""Measure branch-local undefinedness with many independently conditional providers."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmarks.common import Environment, TimingSummary, environment, project_root, summarize
from research.native_backend import (
    AppExpression,
    Application,
    AssignmentHead,
    Atom,
    AtomHead,
    Choice,
    Comparison,
    ComparisonOperator,
    ConstantExpression,
    Definition,
    Integer,
    NativeProgram,
    NativeRule,
    NativeSolver,
    NativeWorkMetrics,
    NVariable,
    NVariableExpression,
    Seed,
    Symbol,
    Variable,
)
from research.native_backend.differential import compare_with_reference


@dataclass(frozen=True, slots=True)
class DynamicUndefinednessMeasurement:
    """Timing and deterministic propagator work for one provider count."""

    solve: TimingSummary
    total: TimingSummary
    model_count: int
    work: NativeWorkMetrics


@dataclass(frozen=True, slots=True)
class DynamicUndefinednessCase:
    """One complete native/reference comparison and native measurement."""

    providers: int
    native: DynamicUndefinednessMeasurement
    visible_models_equal: bool
    reference_sha256: str
    native_sha256: str


@dataclass(frozen=True, slots=True)
class DynamicUndefinednessRun:
    """Machine-readable result for the dynamic-absence workload."""

    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[DynamicUndefinednessCase, ...]


def dynamic_undefinedness_program(providers: int) -> NativeProgram:
    """Create one optional source with ``providers`` independent activation paths."""

    if providers < 1:
        raise ValueError("provider count must be positive")
    mode = Variable("M")
    sources = tuple(
        Application(f"source_{index}", (Symbol("x"),)) for index in range(1, providers + 1)
    )
    target = Application("target", (Symbol("x"),))
    copied = NVariable("_copied")
    target_value = AppExpression(target)
    comparison = Comparison(
        target_value,
        ComparisonOperator.EQUAL,
        ConstantExpression(Integer(7)),
    )
    return NativeProgram(
        choices=(Choice("mode", mode, 0, providers),),
        seeds=tuple(
            Seed(source, Integer(7), (Atom("mode", (Integer(index),)),))
            for index, source in enumerate(sources, start=1)
        ),
        rules=(
            *(
                NativeRule(
                    f"copy_{index}",
                    AssignmentHead(target, NVariableExpression(copied)),
                    definitions=(Definition(copied, AppExpression(source)),),
                )
                for index, source in enumerate(sources, start=1)
            ),
            NativeRule("present", AtomHead(Atom("present")), comparisons=(comparison,)),
            NativeRule(
                "absent",
                AtomHead(Atom("absent")),
                comparisons=(
                    Comparison(
                        comparison.left,
                        comparison.operator,
                        comparison.right,
                        default_negated=True,
                    ),
                ),
            ),
        ),
    )


def relational_reference(providers: int) -> str:
    """Return the independent relational oracle for the same finite program."""

    seeds = "\n".join(
        f"__bench_value(source_{index}(x),7) :- mode({index})." for index in range(1, providers + 1)
    )
    copies = "\n".join(
        f"__bench_value(target(x),V) :- __bench_value(source_{index}(x),V)."
        for index in range(1, providers + 1)
    )
    return (
        f"1 {{ mode(0..{providers}) }} 1.\n"
        f"{seeds}\n"
        f"{copies}\n"
        "present :- __bench_value(target(x),7).\n"
        "absent :- not __target_is_seven.\n"
        "__target_is_seven :- __bench_value(target(x),7).\n"
        ":- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.\n"
    )


def _digest(models: tuple[tuple[str, ...], ...]) -> str:
    canonical = "\n".join(" ".join(model) for model in models).encode()
    return hashlib.sha256(canonical).hexdigest()


def _measure(
    providers: int,
    *,
    repeats: int,
    warmups: int,
) -> DynamicUndefinednessMeasurement:
    solve_samples: list[float] = []
    total_samples: list[float] = []
    expected_models: int | None = None
    expected_work: NativeWorkMetrics | None = None
    for index in range(warmups + repeats):
        started = time.perf_counter()
        result = NativeSolver().solve(dynamic_undefinedness_program(providers))
        total = time.perf_counter() - started
        if expected_models is None:
            expected_models = result.model_count
            expected_work = result.work_metrics
        elif result.model_count != expected_models or result.work_metrics != expected_work:
            raise RuntimeError("dynamic-undefinedness benchmark changed between repeated runs")
        if index >= warmups:
            solve_samples.append(result.solve_seconds)
            total_samples.append(total)
    if expected_models is None or expected_work is None:
        raise RuntimeError("dynamic-undefinedness benchmark produced no observations")
    return DynamicUndefinednessMeasurement(
        solve=summarize(solve_samples),
        total=summarize(total_samples),
        model_count=expected_models,
        work=expected_work,
    )


def run_workload(
    sizes: tuple[int, ...],
    *,
    repeats: int,
    warmups: int = 1,
) -> DynamicUndefinednessRun:
    """Measure every provider count and verify its complete normalized model set."""

    cases: list[DynamicUndefinednessCase] = []
    for providers in sizes:
        comparison = compare_with_reference(
            dynamic_undefinedness_program(providers),
            relational_reference(providers),
        )
        cases.append(
            DynamicUndefinednessCase(
                providers,
                _measure(providers, repeats=repeats, warmups=warmups),
                comparison.equivalent,
                _digest(comparison.reference),
                _digest(comparison.native),
            )
        )
    return DynamicUndefinednessRun(
        schema_version=1,
        family="dynamic-undefinedness-providers",
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
        parser.error("every provider count must be positive")
    if arguments.repeats < 1 or arguments.warmups < 0:
        parser.error("repeats must be positive and warmups must not be negative")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    result = run_workload(
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
