"""Compare native theory copy overhead with the relational reference family."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmarks.common import (
    Environment,
    GroundObserver,
    Measurement,
    StructuralMetrics,
    TimingSummary,
    environment,
    project_root,
    summarize,
)
from benchmarks.reference_scaling import run_reference
from research.native_backend import (
    AppExpression,
    Application,
    AssignmentHead,
    Atom,
    Choice,
    Definition,
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
class ModelEquivalence:
    """Exact comparison plus reproducible digests of normalized model sets."""

    equivalent: bool
    model_count: int
    reference_sha256: str
    native_sha256: str


@dataclass(frozen=True, slots=True)
class NativeMeasurement:
    """Native structure, timings, and deterministic callback-work counters."""

    structure: StructuralMetrics
    ground: TimingSummary
    solve: TimingSummary
    total: TimingSummary
    propagator_init: TimingSummary
    model_reconstruction: TimingSummary
    model_count: int
    work: NativeWorkMetrics


@dataclass(frozen=True, slots=True)
class ComparisonCase:
    """Reference/native baseline and copy results for one value domain."""

    domain_size: int
    reference_baseline: Measurement
    reference_copy: Measurement
    native_baseline: NativeMeasurement
    native_copy: NativeMeasurement
    model_equivalence: ModelEquivalence


@dataclass(frozen=True, slots=True)
class ComparisonRun:
    """Machine-readable result for the full scaling experiment."""

    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[ComparisonCase, ...]
    memory_measurement: str


def native_program(size: int, *, include_copy: bool) -> NativeProgram:
    """Generate a theory seed family with an optional grounder-inert copy rule."""

    if size < 1:
        raise ValueError("domain size must be positive")
    value = Variable("V")
    argument = Symbol("x")
    source = Application("f", (argument,))
    rules: tuple[NativeRule, ...] = ()
    if include_copy:
        nvariable = NVariable("_v")
        rules = (
            NativeRule(
                "copy",
                AssignmentHead(
                    Application("h", (argument,)),
                    NVariableExpression(nvariable),
                ),
                definitions=(Definition(nvariable, AppExpression(source)),),
            ),
        )
    return NativeProgram(
        choices=(Choice("choose", value, 1, size),),
        seeds=(Seed(source, value, (Atom("choose", (value,)),)),),
        rules=rules,
    )


def _measure_native(
    size: int,
    *,
    include_copy: bool,
    repeats: int,
    warmups: int,
) -> NativeMeasurement:
    ground_samples: list[float] = []
    solve_samples: list[float] = []
    total_samples: list[float] = []
    init_samples: list[float] = []
    reconstruction_samples: list[float] = []
    expected_structure: StructuralMetrics | None = None
    expected_models: int | None = None
    expected_work: NativeWorkMetrics | None = None
    for index in range(warmups + repeats):
        observer = GroundObserver()
        started = time.perf_counter()
        result = NativeSolver().solve(
            native_program(size, include_copy=include_copy),
            observer=observer,
        )
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
        model_count = result.model_count
        if expected_structure is None:
            expected_structure = structure
            expected_models = model_count
            expected_work = result.work_metrics
        elif (
            structure != expected_structure
            or model_count != expected_models
            or result.work_metrics != expected_work
        ):
            raise RuntimeError("native benchmark changed between repeated runs")
        if index >= warmups:
            ground_samples.append(result.ground_seconds)
            solve_samples.append(result.solve_seconds)
            total_samples.append(total)
            init_samples.append(result.propagator_init_seconds)
            reconstruction_samples.append(result.model_reconstruction_seconds)
    if expected_structure is None or expected_models is None or expected_work is None:
        raise RuntimeError("native benchmark produced no observations")
    return NativeMeasurement(
        structure=expected_structure,
        ground=summarize(ground_samples),
        solve=summarize(solve_samples),
        total=summarize(total_samples),
        propagator_init=summarize(init_samples),
        model_reconstruction=summarize(reconstruction_samples),
        model_count=expected_models,
        work=expected_work,
    )


def _digest(models: tuple[tuple[str, ...], ...]) -> str:
    canonical = "\n".join(" ".join(model) for model in models).encode()
    return hashlib.sha256(canonical).hexdigest()


def model_equivalence(size: int) -> ModelEquivalence:
    reference = (
        f"1 {{ choose(1..{size}) }} 1.\n"
        "__bench_value(f(x),V) :- choose(V).\n"
        "__bench_value(h(x),V) :- __bench_value(f(x),V).\n"
    )
    compared = compare_with_reference(
        native_program(size, include_copy=True),
        reference,
    )
    return ModelEquivalence(
        equivalent=compared.equivalent,
        model_count=len(compared.native),
        reference_sha256=_digest(compared.reference),
        native_sha256=_digest(compared.native),
    )


def run_comparison(
    sizes: tuple[int, ...],
    *,
    repeats: int,
    warmups: int = 1,
) -> ComparisonRun:
    """Measure both encodings and verify exhaustive visible-model equivalence."""

    reference = run_reference(sizes, repeats=repeats, warmups=warmups)
    cases = tuple(
        ComparisonCase(
            domain_size=size,
            reference_baseline=reference_case.baseline,
            reference_copy=reference_case.copy,
            native_baseline=_measure_native(
                size,
                include_copy=False,
                repeats=repeats,
                warmups=warmups,
            ),
            native_copy=_measure_native(
                size,
                include_copy=True,
                repeats=repeats,
                warmups=warmups,
            ),
            model_equivalence=model_equivalence(size),
        )
        for size, reference_case in zip(sizes, reference.cases, strict=True)
    )
    return ComparisonRun(
        schema_version=2,
        family="nvariable-copy-native-vs-reference",
        repeats=repeats,
        warmups=warmups,
        environment=environment(project_root()),
        cases=cases,
        memory_measurement=reference.memory_measurement,
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 100, 1000, 5000, 10000])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if any(size < 1 for size in arguments.sizes):
        parser.error("every domain size must be positive")
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
