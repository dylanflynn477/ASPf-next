"""Separate grounding, search/enumeration, reconstruction, and digest costs."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import clingo

from benchmarks.common import Environment, TimingSummary, environment, project_root, summarize
from benchmarks.native_vs_reference import native_program
from research.native_backend import NativeSolver, NativeWorkMetrics


@dataclass(frozen=True, slots=True)
class Mode:
    """One model-consumption boundary."""

    name: str
    model_limit: int
    collect_visible: bool


MODES = (
    Mode("first-model", 1, False),
    Mode("fixed-10", 10, False),
    Mode("exhaustive-raw", 0, False),
    Mode("exhaustive-visible", 0, True),
)


@dataclass(frozen=True, slots=True)
class ReconstructionTiming:
    """Detailed native visible-output costs."""

    snapshot_build: TimingSummary
    snapshot_lookup: TimingSummary
    symbol_extraction: TimingSummary
    ordinary_render: TimingSummary
    assignment_render: TimingSummary
    undefined_render: TimingSummary
    model_storage: TimingSummary
    model_sort: TimingSummary
    normalized_digest: TimingSummary


@dataclass(frozen=True, slots=True)
class ModeMeasurement:
    """Repeated observations for one representation and consumption mode."""

    model_count: int
    ground: TimingSummary
    solve: TimingSummary
    total: TimingSummary
    visible_reconstruction: TimingSummary
    normalized_digest: str | None
    native_init: TimingSummary | None
    native_reconstruction: ReconstructionTiming | None
    native_work: NativeWorkMetrics | None


@dataclass(frozen=True, slots=True)
class ModeComparison:
    """Reference and native observations for one mode."""

    mode: Mode
    reference: ModeMeasurement
    native: ModeMeasurement
    visible_models_equal: bool | None


@dataclass(frozen=True, slots=True)
class DecompositionCase:
    """All consumption modes for one candidate domain."""

    domain_size: int
    modes: tuple[ModeComparison, ...]


@dataclass(frozen=True, slots=True)
class DecompositionRun:
    """Machine-readable solve/output decomposition result."""

    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[DecompositionCase, ...]


def _digest(models: tuple[tuple[str, ...], ...]) -> str:
    canonical = "\n".join(" ".join(model) for model in models).encode()
    return hashlib.sha256(canonical).hexdigest()


def _reference_source(size: int) -> str:
    return (
        f"1 {{ choose(1..{size}) }} 1.\n"
        "__bench_value(f(x),V) :- choose(V).\n"
        "__bench_value(h(x),V) :- __bench_value(f(x),V).\n"
    )


def _reference_visible(symbols: list[clingo.Symbol]) -> tuple[str, ...]:
    visible: list[str] = []
    for symbol in symbols:
        if (
            symbol.type is clingo.SymbolType.Function
            and symbol.name == "__bench_value"
            and len(symbol.arguments) == 2
        ):
            visible.append(f"{symbol.arguments[0]}#={symbol.arguments[1]}")
        elif not (symbol.type is clingo.SymbolType.Function and symbol.name.startswith("__")):
            visible.append(str(symbol))
    return tuple(sorted(visible))


def _measure_reference(
    size: int,
    mode: Mode,
    *,
    repeats: int,
    warmups: int,
) -> ModeMeasurement:
    ground_samples: list[float] = []
    solve_samples: list[float] = []
    total_samples: list[float] = []
    reconstruction_samples: list[float] = []
    digest_samples: list[float] = []
    expected_count: int | None = None
    expected_digest: str | None = None
    for index in range(warmups + repeats):
        started = time.perf_counter()
        control = clingo.Control([str(mode.model_limit), "--stats=2", "-t1"])
        control.add("base", [], _reference_source(size))
        ground_started = time.perf_counter()
        control.ground([("base", [])])
        ground_seconds = time.perf_counter() - ground_started
        models: list[tuple[str, ...]] = []
        model_count = 0
        reconstruction_seconds = 0.0
        solve_started = time.perf_counter()
        with control.solve(yield_=True) as handle:
            for model in handle:
                model_count += 1
                if mode.collect_visible:
                    reconstruction_started = time.perf_counter()
                    models.append(_reference_visible(model.symbols(atoms=True)))
                    reconstruction_seconds += time.perf_counter() - reconstruction_started
        solve_seconds = time.perf_counter() - solve_started
        digest_started = time.perf_counter()
        digest = _digest(tuple(sorted(models))) if mode.collect_visible else None
        digest_seconds = time.perf_counter() - digest_started
        total_seconds = time.perf_counter() - started
        if expected_count is None:
            expected_count = model_count
            expected_digest = digest
        elif model_count != expected_count or digest != expected_digest:
            raise RuntimeError("reference decomposition changed between repeated runs")
        if index >= warmups:
            ground_samples.append(ground_seconds)
            solve_samples.append(solve_seconds)
            total_samples.append(total_seconds)
            reconstruction_samples.append(reconstruction_seconds)
            digest_samples.append(digest_seconds)
    if expected_count is None:
        raise RuntimeError("reference decomposition produced no observations")
    return ModeMeasurement(
        model_count=expected_count,
        ground=summarize(ground_samples),
        solve=summarize(solve_samples),
        total=summarize(total_samples),
        visible_reconstruction=summarize(reconstruction_samples),
        normalized_digest=expected_digest,
        native_init=None,
        native_reconstruction=None,
        native_work=None,
    )


def _measure_native(
    size: int,
    mode: Mode,
    *,
    repeats: int,
    warmups: int,
) -> ModeMeasurement:
    ground_samples: list[float] = []
    solve_samples: list[float] = []
    total_samples: list[float] = []
    reconstruction_samples: list[float] = []
    init_samples: list[float] = []
    snapshot_build_samples: list[float] = []
    snapshot_lookup_samples: list[float] = []
    symbol_extraction_samples: list[float] = []
    ordinary_render_samples: list[float] = []
    assignment_render_samples: list[float] = []
    undefined_render_samples: list[float] = []
    storage_samples: list[float] = []
    sort_samples: list[float] = []
    digest_samples: list[float] = []
    expected_count: int | None = None
    expected_digest: str | None = None
    expected_work: NativeWorkMetrics | None = None
    for index in range(warmups + repeats):
        started = time.perf_counter()
        result = NativeSolver().solve(
            native_program(size, include_copy=True),
            model_limit=mode.model_limit,
            collect_models=mode.collect_visible,
            profile_reconstruction=mode.collect_visible,
        )
        digest_started = time.perf_counter()
        digest = (
            _digest(tuple(model.visible for model in result.models))
            if mode.collect_visible
            else None
        )
        digest_seconds = time.perf_counter() - digest_started
        total_seconds = time.perf_counter() - started
        profile = result.reconstruction_profile
        if mode.collect_visible and profile is None:
            raise RuntimeError("native visible mode lacks reconstruction profile")
        if expected_count is None:
            expected_count = result.model_count
            expected_digest = digest
            expected_work = result.work_metrics
        elif (
            result.model_count != expected_count
            or digest != expected_digest
            or result.work_metrics != expected_work
        ):
            raise RuntimeError("native decomposition changed between repeated runs")
        if index >= warmups:
            ground_samples.append(result.ground_seconds)
            solve_samples.append(result.solve_seconds)
            total_samples.append(total_seconds)
            reconstruction_samples.append(result.model_reconstruction_seconds)
            init_samples.append(result.propagator_init_seconds)
            snapshot_build_samples.append(result.snapshot_build_seconds)
            digest_samples.append(digest_seconds)
            snapshot_lookup_samples.append(
                0.0 if profile is None else profile.snapshot_lookup_seconds
            )
            symbol_extraction_samples.append(
                0.0 if profile is None else profile.symbol_extraction_seconds
            )
            ordinary_render_samples.append(
                0.0 if profile is None else profile.ordinary_render_seconds
            )
            assignment_render_samples.append(
                0.0 if profile is None else profile.assignment_render_seconds
            )
            undefined_render_samples.append(
                0.0 if profile is None else profile.undefined_render_seconds
            )
            storage_samples.append(0.0 if profile is None else profile.model_storage_seconds)
            sort_samples.append(0.0 if profile is None else profile.model_sort_seconds)
    if expected_count is None or expected_work is None:
        raise RuntimeError("native decomposition produced no observations")
    detailed = None
    if mode.collect_visible:
        detailed = ReconstructionTiming(
            snapshot_build=summarize(snapshot_build_samples),
            snapshot_lookup=summarize(snapshot_lookup_samples),
            symbol_extraction=summarize(symbol_extraction_samples),
            ordinary_render=summarize(ordinary_render_samples),
            assignment_render=summarize(assignment_render_samples),
            undefined_render=summarize(undefined_render_samples),
            model_storage=summarize(storage_samples),
            model_sort=summarize(sort_samples),
            normalized_digest=summarize(digest_samples),
        )
    return ModeMeasurement(
        model_count=expected_count,
        ground=summarize(ground_samples),
        solve=summarize(solve_samples),
        total=summarize(total_samples),
        visible_reconstruction=summarize(reconstruction_samples),
        normalized_digest=expected_digest,
        native_init=summarize(init_samples),
        native_reconstruction=detailed,
        native_work=expected_work,
    )


def run_decomposition(
    sizes: tuple[int, ...],
    *,
    repeats: int,
    warmups: int = 1,
) -> DecompositionRun:
    """Run every model-consumption boundary for both representations."""

    cases: list[DecompositionCase] = []
    for size in sizes:
        comparisons: list[ModeComparison] = []
        for mode in MODES:
            reference = _measure_reference(size, mode, repeats=repeats, warmups=warmups)
            native = _measure_native(size, mode, repeats=repeats, warmups=warmups)
            equality = None
            if mode.collect_visible:
                equality = reference.normalized_digest == native.normalized_digest
            comparisons.append(ModeComparison(mode, reference, native, equality))
        cases.append(DecompositionCase(size, tuple(comparisons)))
    return DecompositionRun(
        schema_version=1,
        family="nvariable-copy-solve-output-decomposition",
        repeats=repeats,
        warmups=warmups,
        environment=environment(project_root()),
        cases=tuple(cases),
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
    result = run_decomposition(
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
