"""Shared, typed benchmark measurement support."""

from __future__ import annotations

import os
import platform
import statistics
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import clingo


class GroundObserver(clingo.Observer):
    """Count callbacks emitted by Clingo's grounder."""

    def __init__(self) -> None:
        self.rules = 0
        self.weight_rules = 0
        self.theory_atoms = 0

    def rule(self, choice: bool, head: Sequence[int], body: Sequence[int]) -> None:
        del choice, head, body
        self.rules += 1

    def weight_rule(
        self,
        choice: bool,
        head: Sequence[int],
        lower_bound: int,
        body: Sequence[tuple[int, int]],
    ) -> None:
        del choice, head, lower_bound, body
        self.weight_rules += 1

    def theory_atom(
        self,
        atom_id_or_zero: int,
        term_id: int,
        elements: Sequence[int],
    ) -> None:
        del atom_id_or_zero, term_id, elements
        self.theory_atoms += 1

    def theory_atom_with_guard(
        self,
        atom_id_or_zero: int,
        term_id: int,
        elements: Sequence[int],
        operator_id: int,
        right_hand_side_id: int,
    ) -> None:
        del atom_id_or_zero, term_id, elements, operator_id, right_hand_side_id
        self.theory_atoms += 1


@dataclass(frozen=True, slots=True)
class StructuralMetrics:
    """Deterministic metrics for one grounded program."""

    observer_rules: int
    observer_weight_rules: int
    symbolic_atoms: int
    theory_atoms: int
    statistics_rules: int | None
    statistics_atoms: int | None
    statistics_bodies: int | None


@dataclass(frozen=True, slots=True)
class TimingSummary:
    """Median and interquartile range for repeated durations."""

    median_seconds: float
    iqr_seconds: float
    samples_seconds: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class Measurement:
    """Structural, timing, and semantic observations for one case."""

    structure: StructuralMetrics
    ground: TimingSummary
    solve: TimingSummary
    total: TimingSummary
    model_count: int


@dataclass(frozen=True, slots=True)
class GroundMeasurement:
    """Structural and repeated ground-time observations without solving."""

    structure: StructuralMetrics
    ground: TimingSummary


@dataclass(frozen=True, slots=True)
class Environment:
    """Environment metadata required to interpret a benchmark result."""

    benchmark_date_utc: str
    commit: str
    python: str
    clingo: str
    platform: str
    architecture: str
    processor: str
    cpu_count: int | None


def _quartile_range(samples: Sequence[float]) -> float:
    if len(samples) < 2:
        return 0.0
    quartiles = statistics.quantiles(samples, n=4, method="inclusive")
    return quartiles[2] - quartiles[0]


def summarize(samples: Sequence[float]) -> TimingSummary:
    """Summarize timing observations without overstating precision."""

    values = tuple(samples)
    return TimingSummary(statistics.median(values), _quartile_range(values), values)


def environment(project_root: Path) -> Environment:
    """Capture a result's runtime and repository identity."""

    commit_result = subprocess.run(
        ["git", "-c", f"safe.directory={project_root.as_posix()}", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return Environment(
        benchmark_date_utc=datetime.now(UTC).date().isoformat(),
        commit=commit_result.stdout.strip(),
        python=platform.python_version(),
        clingo=clingo.__version__,
        platform=platform.platform(),
        architecture=platform.machine(),
        processor=platform.processor() or "unavailable",
        cpu_count=os.cpu_count(),
    )


def measure_clingo_source(
    source_factory: Callable[[], str],
    *,
    repeats: int,
    warmups: int = 1,
) -> Measurement:
    """Ground and exhaustively solve a deterministic source repeatedly."""

    if repeats < 1:
        raise ValueError("repeats must be positive")
    if warmups < 0:
        raise ValueError("warmups must not be negative")

    ground_samples: list[float] = []
    solve_samples: list[float] = []
    total_samples: list[float] = []
    expected_structure: StructuralMetrics | None = None
    expected_models: int | None = None

    for index in range(warmups + repeats):
        started = time.perf_counter()
        control = clingo.Control(["0", "--stats=2", "-t1"])
        observer = GroundObserver()
        control.register_observer(observer)
        control.add("base", [], source_factory())

        ground_started = time.perf_counter()
        control.ground([("base", [])])
        ground_duration = time.perf_counter() - ground_started

        solve_started = time.perf_counter()
        model_count = 0
        with control.solve(yield_=True) as handle:
            for _model in handle:
                model_count += 1
        solve_duration = time.perf_counter() - solve_started
        total_duration = time.perf_counter() - started

        lp_statistics = control.statistics["problem"]["lp"]
        structure = StructuralMetrics(
            observer_rules=observer.rules,
            observer_weight_rules=observer.weight_rules,
            symbolic_atoms=len(list(control.symbolic_atoms)),
            theory_atoms=observer.theory_atoms,
            statistics_rules=round(lp_statistics["rules"]),
            statistics_atoms=round(lp_statistics["atoms"]),
            statistics_bodies=round(lp_statistics["bodies"]),
        )
        if expected_structure is None:
            expected_structure = structure
            expected_models = model_count
        elif structure != expected_structure or model_count != expected_models:
            raise RuntimeError("benchmark structure or model count changed between repeats")

        if index >= warmups:
            ground_samples.append(ground_duration)
            solve_samples.append(solve_duration)
            total_samples.append(total_duration)

    if expected_structure is None or expected_models is None:
        raise RuntimeError("benchmark produced no observations")
    return Measurement(
        structure=expected_structure,
        ground=summarize(ground_samples),
        solve=summarize(solve_samples),
        total=summarize(total_samples),
        model_count=expected_models,
    )


def measure_ground_source(
    source_factory: Callable[[], str],
    *,
    repeats: int,
    warmups: int = 1,
) -> GroundMeasurement:
    """Measure grounding alone, suitable for large structural cases."""

    if repeats < 1:
        raise ValueError("repeats must be positive")
    if warmups < 0:
        raise ValueError("warmups must not be negative")
    samples: list[float] = []
    expected_structure: StructuralMetrics | None = None
    for index in range(warmups + repeats):
        control = clingo.Control(["0", "--stats=2", "-t1"])
        observer = GroundObserver()
        control.register_observer(observer)
        control.add("base", [], source_factory())
        started = time.perf_counter()
        control.ground([("base", [])])
        duration = time.perf_counter() - started
        structure = StructuralMetrics(
            observer_rules=observer.rules,
            observer_weight_rules=observer.weight_rules,
            symbolic_atoms=len(list(control.symbolic_atoms)),
            theory_atoms=observer.theory_atoms,
            statistics_rules=None,
            statistics_atoms=None,
            statistics_bodies=None,
        )
        if expected_structure is None:
            expected_structure = structure
        elif structure != expected_structure:
            raise RuntimeError("grounding structure changed between repeats")
        if index >= warmups:
            samples.append(duration)
    if expected_structure is None:
        raise RuntimeError("grounding benchmark produced no observations")
    return GroundMeasurement(expected_structure, summarize(samples))


def project_root() -> Path:
    """Return the repository root for commands and metadata."""

    return Path(__file__).resolve().parents[1]
