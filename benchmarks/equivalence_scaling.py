"""Run one exhaustive visible-model comparison per requested domain size."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmarks.common import Environment, environment, project_root
from benchmarks.native_vs_reference import ModelEquivalence, model_equivalence


@dataclass(frozen=True, slots=True)
class EquivalenceCase:
    domain_size: int
    result: ModelEquivalence


@dataclass(frozen=True, slots=True)
class EquivalenceRun:
    schema_version: int
    family: str
    repeats: int
    environment: Environment
    cases: tuple[EquivalenceCase, ...]


def run_equivalence(sizes: tuple[int, ...]) -> EquivalenceRun:
    """Compare complete model sets once; this is not a timing benchmark."""

    return EquivalenceRun(
        schema_version=1,
        family="nvariable-copy-visible-model-equivalence",
        repeats=1,
        environment=environment(project_root()),
        cases=tuple(EquivalenceCase(size, model_equivalence(size)) for size in sizes),
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[5000, 10000])
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if any(size < 1 for size in arguments.sizes):
        parser.error("every domain size must be positive")
    return arguments


def main() -> int:
    arguments = _arguments()
    result = run_equivalence(tuple(arguments.sizes))
    rendered = json.dumps(asdict(result), indent=2) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
