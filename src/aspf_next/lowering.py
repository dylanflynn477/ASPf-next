"""Correctness-oriented reference lowering from ASP{f} IR to ordinary Clingo."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aspf_next.ir import (
    AspfStatement,
    GroundTermKind,
    NAtom,
    NAtomOperator,
    NAtomRole,
    OrdinaryStatement,
    Program,
)

INTERNAL_VALUE_PREDICATE = "__aspf_value"
INTERNAL_INTEGER_PREDICATE = "__aspf_integer"
INTERNAL_DEFINITIONS = (
    f"#defined {INTERNAL_VALUE_PREDICATE}/2.\n#defined {INTERNAL_INTEGER_PREDICATE}/1."
)
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
        integer_values = sorted(
            {
                n_atom.value.text
                for statement in program.statements
                if isinstance(statement, AspfStatement)
                for n_atom in statement.n_atoms
                if n_atom.role is NAtomRole.HEAD
                and n_atom.operator is NAtomOperator.EQUAL
                and n_atom.value.kind is GroundTermKind.INTEGER
            },
            key=int,
        )
        source += "".join(f"{INTERNAL_INTEGER_PREDICATE}({value}).\n" for value in integer_values)
        source += f"{INTERNAL_DEFINITIONS}\n"
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
            variable_stem = "_AspfCmp" if n_atom.operator.is_ordered else "_AspfNeq"
            value_variable = f"{variable_stem}{variable_index}"
            while value_variable in identifiers:
                variable_index += 1
                value_variable = f"{variable_stem}{variable_index}"
            identifiers.add(value_variable)
            variable_index += 1
            lookup_predicate = (
                INTERNAL_INTEGER_PREDICATE
                if n_atom.operator.is_ordered
                else INTERNAL_VALUE_PREDICATE
            )
            lookups = [
                f"{INTERNAL_VALUE_PREDICATE}({n_atom.application.render()},{value_variable})"
            ]
            if lookup_predicate != INTERNAL_VALUE_PREDICATE:
                lookups.append(f"{lookup_predicate}({value_variable})")
            lookups.append(f"{value_variable} {n_atom.operator.clingo_symbol} {n_atom.value.text}")
            replacement = ", ".join(lookups)
        replacements.append((local_start, local_end, replacement))

    for start, end, replacement in sorted(replacements, reverse=True):
        text = f"{text[:start]}{replacement}{text[end:]}"
    return text
