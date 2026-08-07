"""Correctness-oriented reference lowering from ASP{f} IR to ordinary Clingo."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aspf_next.ir import AspfStatement, NAtom, NAtomOperator, OrdinaryStatement, Program

INTERNAL_VALUE_PREDICATE = "__aspf_value"
FUNCTIONALITY_CONSTRAINT = ":- __aspf_value(K,V1), __aspf_value(K,V2), V1 != V2."
_IDENTIFIER = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])")


@dataclass(frozen=True, slots=True)
class LoweredProgram:
    """Ordinary Clingo source produced by the reference backend."""

    source: str
    origin: str


def lower_program(program: Program) -> LoweredProgram:
    """Lower supported n-atoms and append partial-function functionality."""

    pieces: list[str] = []
    for statement in program.statements:
        if isinstance(statement, OrdinaryStatement):
            pieces.append(statement.text)
        else:
            pieces.append(_lower_statement(statement))

    source = "".join(pieces)
    if program.declarations:
        if source and not source.endswith("\n"):
            source += "\n"
        source += f"{FUNCTIONALITY_CONSTRAINT}\n"
    return LoweredProgram(source, program.filename)


def render_internal_atom(n_atom: NAtom) -> str:
    """Render the ordinary predicate used by the reference backend."""

    return f"{INTERNAL_VALUE_PREDICATE}({n_atom.application.render()},{n_atom.value.text})"


def _lower_statement(statement: AspfStatement) -> str:
    text = statement.text
    replacements: list[tuple[int, int, str]] = []
    identifiers = set(_IDENTIFIER.findall(text))
    variable_index = 0
    for n_atom in statement.n_atoms:
        local_start = n_atom.span.start - statement.span.start
        local_end = n_atom.span.end - statement.span.start
        if n_atom.operator is NAtomOperator.EQUAL:
            replacement = render_internal_atom(n_atom)
        else:
            value_variable = f"_AspfNeq{variable_index}"
            while value_variable in identifiers:
                variable_index += 1
                value_variable = f"_AspfNeq{variable_index}"
            identifiers.add(value_variable)
            variable_index += 1
            replacement = (
                f"{INTERNAL_VALUE_PREDICATE}"
                f"({n_atom.application.render()},{value_variable}), "
                f"{value_variable} != {n_atom.value.text}"
            )
        replacements.append((local_start, local_end, replacement))

    for start, end, replacement in sorted(replacements, reverse=True):
        text = f"{text[:start]}{replacement}{text[end:]}"
    return text
