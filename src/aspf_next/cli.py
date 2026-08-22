"""Command-line interface for the first ASP{f}-next milestone."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from aspf_next import __version__
from aspf_next.errors import AspfNextError
from aspf_next.frontend import parse_sources
from aspf_next.lowering import lower_program
from aspf_next.solver import SolveResult, solve_program
from aspf_next.source import SourceText


def build_parser() -> argparse.ArgumentParser:
    """Construct the public argument parser."""

    parser = argparse.ArgumentParser(
        prog="aspf",
        description="Run the restricted ASP{f} compatibility frontend on Clingo 5.8.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("files", metavar="FILE", nargs="+", type=Path)
    parser.add_argument(
        "--models",
        type=_nonnegative_int,
        default=1,
        metavar="N",
        help="maximum models to enumerate; 0 requests all (default: 1)",
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--emit-lowered",
        action="store_true",
        help="print the ordinary Clingo reference translation and exit",
    )
    output.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit normalized machine-readable results",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a conventional process status."""

    args = build_parser().parse_args(argv)
    try:
        sources = tuple(
            SourceText(path.read_text(encoding="utf-8"), str(path)) for path in args.files
        )
        program = parse_sources(sources)
        if args.emit_lowered:
            print(lower_program(program).source, end="")
            return 0
        result = solve_program(program, models=args.models)
    except (AspfNextError, OSError) as error:
        print(f"aspf: error: {error}", file=sys.stderr)
        return 2

    if args.json_output:
        _print_json(result, sys.stdout)
    else:
        _print_human(result, sys.stdout)
    return 0


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or a positive integer")
    return parsed


def _print_human(result: SolveResult, stream: TextIO) -> None:
    for index, model in enumerate(result.models, start=1):
        print(f"Answer: {index}", file=stream)
        print(model.render(), file=stream)
    print(result.status.value, file=stream)


def _print_json(result: SolveResult, stream: TextIO) -> None:
    payload = {
        "status": result.status.value,
        "model_count": len(result.models),
        "models": [model.to_json() for model in result.models],
        "exhausted": result.exhausted,
    }
    json.dump(payload, stream, indent=2, sort_keys=True)
    print(file=stream)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
