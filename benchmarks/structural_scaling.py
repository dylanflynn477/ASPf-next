"""Measure grounding structure without exhaustive solving at large domains."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path

from benchmarks.common import (
    Environment,
    GroundMeasurement,
    environment,
    measure_ground_source,
    project_root,
)
from benchmarks.native_vs_reference import native_program
from benchmarks.reference_scaling import reference_source
from research.native_backend.compiler import compile_program


@dataclass(frozen=True, slots=True)
class StructuralCase:
    domain_size: int
    reference_baseline: GroundMeasurement
    reference_copy: GroundMeasurement
    native_baseline: GroundMeasurement
    native_copy: GroundMeasurement


@dataclass(frozen=True, slots=True)
class StructuralRun:
    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[StructuralCase, ...]
    solve_scope: str


def _native_source(size: int, *, include_copy: bool) -> str:
    return compile_program(native_program(size, include_copy=include_copy))


def run_structural(
    sizes: tuple[int, ...],
    *,
    repeats: int,
    warmups: int = 1,
) -> StructuralRun:
    """Measure all four ground programs without invoking solve."""

    cases = tuple(
        StructuralCase(
            domain_size=size,
            reference_baseline=measure_ground_source(
                partial(reference_source, size, include_copy=False),
                repeats=repeats,
                warmups=warmups,
            ),
            reference_copy=measure_ground_source(
                partial(reference_source, size, include_copy=True),
                repeats=repeats,
                warmups=warmups,
            ),
            native_baseline=measure_ground_source(
                partial(_native_source, size, include_copy=False),
                repeats=repeats,
                warmups=warmups,
            ),
            native_copy=measure_ground_source(
                partial(_native_source, size, include_copy=True),
                repeats=repeats,
                warmups=warmups,
            ),
        )
        for size in sizes
    )
    return StructuralRun(
        schema_version=1,
        family="nvariable-copy-grounding-only",
        repeats=repeats,
        warmups=warmups,
        environment=environment(project_root()),
        cases=cases,
        solve_scope="none; this runner isolates grounding and records no model-count claim",
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 100, 1000, 5000, 10000])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if any(size < 1 for size in arguments.sizes):
        parser.error("every domain size must be positive")
    return arguments


def main() -> int:
    arguments = _arguments()
    result = run_structural(
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
