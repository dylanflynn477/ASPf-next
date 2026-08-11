"""Normalize visible native and relational-reference models for comparison."""

from __future__ import annotations

from dataclasses import dataclass

import clingo

from research.native_backend.ir import NativeProgram
from research.native_backend.solver import NativeSolver


@dataclass(frozen=True, slots=True)
class DifferentialResult:
    """Normalized exhaustive model sets for two research encodings."""

    native: tuple[tuple[str, ...], ...]
    reference: tuple[tuple[str, ...], ...]

    @property
    def equivalent(self) -> bool:
        return self.native == self.reference


def _relation_assignment(symbol: clingo.Symbol, predicate: str) -> str | None:
    if (
        symbol.type is not clingo.SymbolType.Function
        or symbol.name != predicate
        or len(symbol.arguments) != 2
    ):
        return None
    return f"{symbol.arguments[0]}#={symbol.arguments[1]}"


def normalize_reference_models(
    source: str,
    *,
    relation_predicate: str = "__bench_value",
) -> tuple[tuple[str, ...], ...]:
    """Solve and normalize ordinary atoms plus one private value relation."""

    control = clingo.Control(["0", "-t1"])
    control.add("base", [], source)
    control.ground([("base", [])])
    models: list[tuple[str, ...]] = []
    with control.solve(yield_=True) as handle:
        for model in handle:
            visible: list[str] = []
            for symbol in model.symbols(atoms=True):
                assignment = _relation_assignment(symbol, relation_predicate)
                if assignment is not None:
                    visible.append(assignment)
                elif not (
                    symbol.type is clingo.SymbolType.Function and symbol.name.startswith("__")
                ):
                    visible.append(str(symbol))
            models.append(tuple(sorted(visible)))
    return tuple(sorted(models))


def compare_with_reference(
    program: NativeProgram,
    reference_source: str,
    *,
    relation_predicate: str = "__bench_value",
) -> DifferentialResult:
    """Compare normalized visible semantics, never raw private atom sets."""

    native_result = NativeSolver().solve(program)
    native = tuple(sorted(model.visible for model in native_result.models))
    reference = normalize_reference_models(
        reference_source,
        relation_predicate=relation_predicate,
    )
    return DifferentialResult(native=native, reference=reference)
