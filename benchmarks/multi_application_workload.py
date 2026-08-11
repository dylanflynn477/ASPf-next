"""Measure a small multi-application, partially undefined native workload."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path

from benchmarks.common import (
    Environment,
    GroundObserver,
    Measurement,
    StructuralMetrics,
    TimingSummary,
    environment,
    measure_clingo_source,
    project_root,
    summarize,
)
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
class NativeWorkloadMeasurement:
    """Native structural, timing, and callback observations."""

    structure: StructuralMetrics
    ground: TimingSummary
    solve: TimingSummary
    total: TimingSummary
    model_reconstruction: TimingSummary
    model_count: int
    work: NativeWorkMetrics


@dataclass(frozen=True, slots=True)
class WorkloadCase:
    """One candidate-domain size in both equivalent representations."""

    candidate_values: int
    reference: Measurement
    native: NativeWorkloadMeasurement
    visible_models_equal: bool
    reference_sha256: str
    native_sha256: str


@dataclass(frozen=True, slots=True)
class WorkloadRun:
    """Machine-readable moderately realistic workload result."""

    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[WorkloadCase, ...]


def _application(function: str, device: Symbol | Variable) -> Application:
    return Application(function, (device,))


def native_workload(candidate_values: int) -> NativeProgram:
    """Create a three-device observation pipeline with one undefined source."""

    if candidate_values < 1:
        raise ValueError("candidate domain size must be positive")
    device = Variable("D")
    value = Variable("V")
    device_atom = Atom("device", (device,))
    available_atom = Atom("available", (device,))
    choose_atom = Atom("choose", (value,))
    observed = NVariable("_observed")
    limit = NVariable("_limit")
    copied = NVariable("_copied")
    raw = _application("raw", device)
    reading = _application("reading", device)
    threshold = _application("threshold", device)
    return NativeProgram(
        facts=(
            Atom("device", (Symbol("d1"),)),
            Atom("device", (Symbol("d2"),)),
            Atom("device", (Symbol("d3"),)),
            Atom("available", (Symbol("d1"),)),
            Atom("available", (Symbol("d2"),)),
        ),
        choices=(Choice("choose", value, 1, candidate_values),),
        seeds=(
            Seed(raw, value, (available_atom, choose_atom)),
            Seed(threshold, Integer(2), (device_atom,)),
        ),
        rules=(
            NativeRule(
                "copy_reading",
                AssignmentHead(reading, NVariableExpression(copied)),
                definitions=(Definition(copied, AppExpression(raw)),),
                when=(device_atom,),
            ),
            NativeRule(
                "classify",
                AssignmentHead(
                    _application("status", device), ConstantExpression(Symbol("active"))
                ),
                comparisons=(
                    Comparison(
                        AppExpression(reading),
                        ComparisonOperator.GREATER,
                        ConstantExpression(Integer(0)),
                    ),
                ),
                when=(device_atom,),
            ),
            NativeRule(
                "ready",
                AtomHead(Atom("ready", (device,))),
                definitions=(
                    Definition(observed, AppExpression(reading)),
                    Definition(limit, AppExpression(threshold)),
                ),
                comparisons=(
                    Comparison(
                        NVariableExpression(observed),
                        ComparisonOperator.GREATER_EQUAL,
                        NVariableExpression(limit),
                    ),
                ),
                when=(device_atom,),
            ),
        ),
    )


def reference_workload(candidate_values: int) -> str:
    """Return the relational approximation for :func:`native_workload`."""

    if candidate_values < 1:
        raise ValueError("candidate domain size must be positive")
    return f"""device(d1). device(d2). device(d3).
available(d1). available(d2).
1 {{ choose(1..{candidate_values}) }} 1.
__bench_value(raw(D),V) :- available(D), choose(V).
__bench_value(threshold(D),2) :- device(D).
__bench_value(reading(D),V) :- device(D), __bench_value(raw(D),V).
__bench_value(status(D),active) :- device(D), __bench_value(reading(D),V), V > 0.
ready(D) :- device(D), __bench_value(reading(D),V),
            __bench_value(threshold(D),L), V >= L.
:- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.
"""


def _digest(models: tuple[tuple[str, ...], ...]) -> str:
    canonical = "\n".join(" ".join(model) for model in models).encode()
    return hashlib.sha256(canonical).hexdigest()


def _measure_native(
    candidate_values: int, *, repeats: int, warmups: int
) -> NativeWorkloadMeasurement:
    ground_samples: list[float] = []
    solve_samples: list[float] = []
    total_samples: list[float] = []
    reconstruction_samples: list[float] = []
    expected_structure: StructuralMetrics | None = None
    expected_models: int | None = None
    expected_work: NativeWorkMetrics | None = None
    for index in range(warmups + repeats):
        observer = GroundObserver()
        started = time.perf_counter()
        result = NativeSolver().solve(native_workload(candidate_values), observer=observer)
        total = time.perf_counter() - started
        structure = StructuralMetrics(
            observer_rules=observer.rules,
            observer_weight_rules=observer.weight_rules,
            symbolic_atoms=result.symbolic_atoms,
            theory_atoms=result.theory_atoms,
            statistics_rules=result.statistics_rules,
            statistics_atoms=result.statistics_atoms,
            statistics_bodies=result.statistics_bodies,
        )
        if expected_structure is None:
            expected_structure = structure
            expected_models = result.model_count
            expected_work = result.work_metrics
        elif (
            structure != expected_structure
            or result.model_count != expected_models
            or result.work_metrics != expected_work
        ):
            raise RuntimeError("native workload changed between repeated runs")
        if index >= warmups:
            ground_samples.append(result.ground_seconds)
            solve_samples.append(result.solve_seconds)
            total_samples.append(total)
            reconstruction_samples.append(result.model_reconstruction_seconds)
    if expected_structure is None or expected_models is None or expected_work is None:
        raise RuntimeError("native workload produced no observations")
    return NativeWorkloadMeasurement(
        structure=expected_structure,
        ground=summarize(ground_samples),
        solve=summarize(solve_samples),
        total=summarize(total_samples),
        model_reconstruction=summarize(reconstruction_samples),
        model_count=expected_models,
        work=expected_work,
    )


def run_workload(sizes: tuple[int, ...], *, repeats: int, warmups: int = 1) -> WorkloadRun:
    """Measure the workload and verify exact exhaustive visible-model equality."""

    cases: list[WorkloadCase] = []
    for size in sizes:
        reference_source = reference_workload(size)
        reference = measure_clingo_source(
            partial(reference_workload, size), repeats=repeats, warmups=warmups
        )
        native = _measure_native(size, repeats=repeats, warmups=warmups)
        comparison = compare_with_reference(native_workload(size), reference_source)
        cases.append(
            WorkloadCase(
                candidate_values=size,
                reference=reference,
                native=native,
                visible_models_equal=comparison.equivalent,
                reference_sha256=_digest(comparison.reference),
                native_sha256=_digest(comparison.native),
            )
        )
    return WorkloadRun(
        schema_version=1,
        family="multi-application-observation-pipeline",
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
        parser.error("every candidate domain size must be positive")
    if arguments.repeats < 1 or arguments.warmups < 0:
        parser.error("repeats must be positive and warmups must not be negative")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    result = run_workload(
        tuple(arguments.sizes), repeats=arguments.repeats, warmups=arguments.warmups
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
