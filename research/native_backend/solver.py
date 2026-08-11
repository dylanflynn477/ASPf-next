"""Solve typed research programs through the isolated native propagator."""

from __future__ import annotations

import time
from dataclasses import dataclass

import clingo

from research.native_backend.compiler import compile_program
from research.native_backend.ir import NativeProgram
from research.native_backend.propagator import NativePropagator, RuleKey


@dataclass(frozen=True, slots=True)
class NativeModel:
    """Normalized user-visible model reconstructed from a native snapshot."""

    ordinary_atoms: tuple[str, ...]
    assignments: tuple[str, ...]
    undefined_nvariables: tuple[str, ...]

    @property
    def visible(self) -> tuple[str, ...]:
        return tuple(sorted((*self.ordinary_atoms, *self.assignments)))


@dataclass(frozen=True, slots=True)
class NativeSolveResult:
    """Exhaustive solve result and structural evidence."""

    satisfiable: bool
    models: tuple[NativeModel, ...]
    internal_source: str
    symbolic_atoms: int
    theory_atoms: int
    statistics_rules: int
    statistics_atoms: int
    statistics_bodies: int
    ground_seconds: float
    solve_seconds: float
    check_count: int
    undo_count: int


def _render_undefined(key: RuleKey, name: str) -> str:
    instance = ",".join(value.render() for value in key.instance)
    suffix = f"[{instance}]" if instance else ""
    return f"{key.identifier}{suffix}:_{name}"


def _private(symbol: clingo.Symbol) -> bool:
    return symbol.type is clingo.SymbolType.Function and symbol.name.startswith("__aspf_")


class NativeSolver:
    """Research-only solver; each call owns independent Clingo and propagator state."""

    def solve(
        self,
        program: NativeProgram,
        *,
        observer: clingo.Observer | None = None,
    ) -> NativeSolveResult:
        source = compile_program(program)
        control = clingo.Control(["0", "--stats=2", "-t1"])
        propagator = NativePropagator()
        control.register_propagator(propagator)
        if observer is not None:
            control.register_observer(observer)
        control.add("base", [], source)

        ground_started = time.perf_counter()
        control.ground([("base", [])])
        ground_seconds = time.perf_counter() - ground_started
        theory_atom_count = len(list(control.theory_atoms))
        symbolic_atom_count = len(list(control.symbolic_atoms))

        models: list[NativeModel] = []
        solve_started = time.perf_counter()
        with control.solve(yield_=True) as handle:
            for model in handle:
                snapshot = propagator.snapshot(model.thread_id)
                ordinary = tuple(
                    sorted(
                        str(symbol) for symbol in model.symbols(shown=True) if not _private(symbol)
                    )
                )
                assignments = tuple(
                    f"{application.render()}#={value.render()}"
                    for application, value in snapshot.assignments
                )
                undefined = tuple(
                    _render_undefined(key, name) for key, name in snapshot.undefined_nvariables
                )
                models.append(NativeModel(ordinary, assignments, undefined))
        solve_seconds = time.perf_counter() - solve_started

        lp_statistics = control.statistics["problem"]["lp"]
        return NativeSolveResult(
            satisfiable=bool(models),
            models=tuple(sorted(models, key=lambda model: model.visible)),
            internal_source=source,
            symbolic_atoms=symbolic_atom_count,
            theory_atoms=theory_atom_count,
            statistics_rules=round(lp_statistics["rules"]),
            statistics_atoms=round(lp_statistics["atoms"]),
            statistics_bodies=round(lp_statistics["bodies"]),
            ground_seconds=ground_seconds,
            solve_seconds=solve_seconds,
            check_count=propagator.check_count,
            undo_count=propagator.undo_count,
        )
