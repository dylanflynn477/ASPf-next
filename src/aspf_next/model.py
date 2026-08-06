"""Normalized model extraction and stable ASP{f}-style rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import clingo

from aspf_next.lowering import INTERNAL_VALUE_PREDICATE

_INTERNAL_PREFIX = "__aspf_"


@dataclass(frozen=True, slots=True)
class NormalizedModel:
    """A model separated into ordinary shown atoms and reconstructed n-atoms."""

    ordinary_atoms: tuple[str, ...]
    assignments: tuple[str, ...]

    @property
    def atoms(self) -> tuple[str, ...]:
        """Return stable human output order: ordinary atoms, then assignments."""

        return self.ordinary_atoms + self.assignments

    def render(self) -> str:
        """Render one Clingo-style answer line without internal predicates."""

        return " ".join(self.atoms)

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "atoms": list(self.atoms),
            "ordinary_atoms": list(self.ordinary_atoms),
            "assignments": list(self.assignments),
        }


def normalize_model(model: clingo.Model) -> NormalizedModel:
    """Extract shown ordinary atoms and all true reference-backend values."""

    ordinary = sorted(
        str(symbol) for symbol in model.symbols(shown=True) if not _is_internal(symbol)
    )
    assignments = sorted(
        _render_assignment(symbol) for symbol in model.symbols(atoms=True) if _is_value_atom(symbol)
    )
    return NormalizedModel(tuple(ordinary), tuple(assignments))


def _is_internal(symbol: clingo.Symbol) -> bool:
    return symbol.type is clingo.SymbolType.Function and symbol.name.startswith(_INTERNAL_PREFIX)


def _is_value_atom(symbol: clingo.Symbol) -> bool:
    return (
        symbol.type is clingo.SymbolType.Function
        and symbol.name == INTERNAL_VALUE_PREDICATE
        and len(symbol.arguments) == 2
    )


def _render_assignment(symbol: clingo.Symbol) -> str:
    key, value = symbol.arguments
    return f"{key}#={value}"
