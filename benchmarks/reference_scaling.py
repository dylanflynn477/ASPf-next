"""Benchmark relational n-variable copy overhead in the reference representation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path

from benchmarks.common import Environment, Measurement, environment, measure_clingo_source
from benchmarks.common import project_root as find_project_root


@dataclass(frozen=True, slots=True)
class ReferenceCase:
    """Baseline and relational-copy observations for one domain size."""

    domain_size: int
    baseline: Measurement
    copy: Measurement


@dataclass(frozen=True, slots=True)
class ReferenceRun:
    """Machine-readable reference benchmark result."""

    schema_version: int
    family: str
    repeats: int
    warmups: int
    environment: Environment
    cases: tuple[ReferenceCase, ...]
    memory_measurement: str


def reference_source(size: int, *, include_copy: bool) -> str:
    """Generate the relation family without manipulating its value universe."""

    if size < 1:
        raise ValueError("domain size must be positive")
    copy_rule = "__bench_value(h(x),V) :- __bench_value(f(x),V).\n" if include_copy else ""
    return f"value(1..{size}).\n1 {{ __bench_value(f(x),V) : value(V) }} 1.\n{copy_rule}"


def run_reference(
    sizes: tuple[int, ...],
    *,
    repeats: int,
    warmups: int = 1,
) -> ReferenceRun:
    """Measure baseline and copy variants for every requested size."""

    cases = tuple(
        ReferenceCase(
            domain_size=size,
            baseline=measure_clingo_source(
                partial(reference_source, size, include_copy=False),
                repeats=repeats,
                warmups=warmups,
            ),
            copy=measure_clingo_source(
                partial(reference_source, size, include_copy=True),
                repeats=repeats,
                warmups=warmups,
            ),
        )
        for size in sizes
    )
    return ReferenceRun(
        schema_version=1,
        family="nvariable-copy-reference",
        repeats=repeats,
        warmups=warmups,
        environment=environment(find_project_root()),
        cases=cases,
        memory_measurement=(
            "omitted: the Python standard library has no portable peak-process-memory "
            "measure comparable across supported platforms"
        ),
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
    result = run_reference(
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
