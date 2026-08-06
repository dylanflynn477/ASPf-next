"""Clingo 5.8 integration for lowered ASP{f} programs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import clingo

from aspf_next.errors import SolverError
from aspf_next.ir import Program
from aspf_next.lowering import LoweredProgram, lower_program
from aspf_next.model import NormalizedModel, normalize_model


class SolveStatus(Enum):
    """Stable public solve statuses."""

    SATISFIABLE = "SATISFIABLE"
    UNSATISFIABLE = "UNSATISFIABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SolveResult:
    """Normalized result of one Clingo solve call."""

    status: SolveStatus
    models: tuple[NormalizedModel, ...]
    exhausted: bool
    lowered: LoweredProgram


def solve_program(program: Program, *, models: int = 1) -> SolveResult:
    """Lower, ground, and enumerate up to ``models`` models; zero means all."""

    if models < 0:
        raise ValueError("models must be zero or a positive integer")

    lowered = lower_program(program)
    control = clingo.Control([f"--models={models}"])
    try:
        control.add("base", [], lowered.source)
        control.ground([("base", [])])
        normalized: list[NormalizedModel] = []
        with control.solve(yield_=True) as handle:
            for model in handle:
                normalized.append(normalize_model(model))
            result = handle.get()
    except RuntimeError as error:
        raise SolverError(f"Clingo rejected the lowered program: {error}") from error

    if result.satisfiable:
        status = SolveStatus.SATISFIABLE
    elif result.unsatisfiable:
        status = SolveStatus.UNSATISFIABLE
    else:
        status = SolveStatus.UNKNOWN
    return SolveResult(status, tuple(normalized), result.exhausted, lowered)
