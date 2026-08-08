"""Correctness-oriented reference lowering from ASP{f} IR to ordinary Clingo."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aspf_next.ir import (
    ApplicationOperand,
    AspfStatement,
    Assignment,
    BodyComparison,
    GroundTermKind,
    NAtomOperator,
    OrdinaryStatement,
    Program,
    ScalarOperand,
    VariableTerm,
)

INTERNAL_VALUE_PREDICATE = "__aspf_value"
INTERNAL_INTEGER_PREDICATE = "__aspf_integer"
INTERNAL_SATISFACTION_PREFIX = "__aspf_sat_"
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


@dataclass(slots=True)
class TemporaryAllocator:
    """Allocate deterministic statement-local variables without collisions."""

    used_identifiers: set[str]
    next_index: int = 0

    def __post_init__(self) -> None:
        self.used_identifiers = set(self.used_identifiers)

    def new(self, stem: str) -> str:
        """Return the first unused ``stem + integer`` name."""

        while True:
            candidate = f"{stem}{self.next_index}"
            self.next_index += 1
            if candidate in self.used_identifiers:
                continue
            self.used_identifiers.add(candidate)
            return candidate


@dataclass(slots=True)
class SatisfactionHelperAllocator:
    """Allocate deterministic program-local helper predicate identities."""

    next_index: int = 0

    def new(self) -> str:
        """Return the next private positive-satisfaction predicate name."""

        name = f"{INTERNAL_SATISFACTION_PREFIX}{self.next_index}"
        self.next_index += 1
        return name


def lower_program(program: Program) -> LoweredProgram:
    """Lower supported n-atoms and append partial-function functionality."""

    pieces: list[str] = []
    helper_rules: list[str] = []
    helper_names = SatisfactionHelperAllocator()
    for statement in program.statements:
        if isinstance(statement, OrdinaryStatement):
            pieces.append(statement.text)
        else:
            lowered_statement, statement_helpers = _lower_statement(statement, helper_names)
            pieces.append(lowered_statement)
            helper_rules.extend(statement_helpers)

    source = "".join(pieces)
    if program.declarations or program.global_nherb:
        if source and not source.endswith("\n"):
            source += "\n"
        if helper_rules:
            source += "".join(f"{rule}\n" for rule in helper_rules)
        integer_values = sorted(
            {
                n_atom.value.text
                for statement in program.statements
                if isinstance(statement, AspfStatement)
                for n_atom in statement.n_atoms
                if isinstance(n_atom, Assignment) and n_atom.value.kind is GroundTermKind.INTEGER
            },
            key=int,
        )
        source += "".join(f"{INTERNAL_INTEGER_PREDICATE}({value}).\n" for value in integer_values)
        source += f"{INTERNAL_DEFINITIONS}\n"
        source += f"{FUNCTIONALITY_CONSTRAINT}\n"
    return LoweredProgram(source, program.filename)


def render_internal_atom(assignment: Assignment) -> str:
    """Render the ordinary predicate used by the reference backend."""

    return _render_value_lookup(assignment.target, assignment.value.text)


def _lower_statement(
    statement: AspfStatement,
    helper_names: SatisfactionHelperAllocator,
) -> tuple[str, tuple[str, ...]]:
    text = statement.text
    replacements: list[tuple[int, int, str]] = []
    helper_rules: list[str] = []
    temps = TemporaryAllocator(set(_IDENTIFIER.findall(text)))
    for n_atom in statement.n_atoms:
        local_start = n_atom.span.start - statement.span.start
        local_end = n_atom.span.end - statement.span.start
        if isinstance(n_atom, Assignment):
            replacement = render_internal_atom(n_atom)
        else:
            positive_body = _lower_comparison(n_atom, temps)
            if n_atom.negated:
                helper = _render_helper_atom(helper_names.new(), _comparison_variables(n_atom))
                helper_rules.append(f"{helper} :- {positive_body}.")
                replacement = f"not {helper}"
            else:
                replacement = positive_body
        replacements.append((local_start, local_end, replacement))

    for start, end, replacement in sorted(replacements, reverse=True):
        text = f"{text[:start]}{replacement}{text[end:]}"
    return text, tuple(helper_rules)


def _lower_comparison(comparison: BodyComparison, temps: TemporaryAllocator) -> str:
    if isinstance(comparison.right, ScalarOperand):
        return _lower_scalar_comparison(comparison, comparison.right, temps)
    return _lower_application_comparison(comparison, comparison.right, temps)


def _lower_scalar_comparison(
    comparison: BodyComparison,
    right: ScalarOperand,
    temps: TemporaryAllocator,
) -> str:
    if comparison.operator is NAtomOperator.EQUAL:
        return _render_value_lookup(comparison.left, right.text)

    stem = "_AspfCmp" if comparison.operator.is_ordered else "_AspfNeq"
    value_variable = temps.new(stem)
    literals = [_render_value_lookup(comparison.left, value_variable)]
    if comparison.operator.is_ordered:
        literals.append(f"{INTERNAL_INTEGER_PREDICATE}({value_variable})")
    literals.append(f"{value_variable} {comparison.operator.clingo_symbol} {right.text}")
    return ", ".join(literals)


def _lower_application_comparison(
    comparison: BodyComparison,
    right: ApplicationOperand,
    temps: TemporaryAllocator,
) -> str:
    left_value = temps.new("_AspfCmp")
    if comparison.operator is NAtomOperator.EQUAL:
        return ", ".join(
            (
                _render_value_lookup(comparison.left, left_value),
                _render_value_lookup(right, left_value),
            )
        )

    right_value = temps.new("_AspfCmp")
    literals = [
        _render_value_lookup(comparison.left, left_value),
        _render_value_lookup(right, right_value),
    ]
    if comparison.operator.is_ordered:
        literals.extend(
            (
                f"{INTERNAL_INTEGER_PREDICATE}({left_value})",
                f"{INTERNAL_INTEGER_PREDICATE}({right_value})",
            )
        )
    literals.append(f"{left_value} {comparison.operator.clingo_symbol} {right_value}")
    return ", ".join(literals)


def _render_value_lookup(application: ApplicationOperand, value: str) -> str:
    return f"{INTERNAL_VALUE_PREDICATE}({application.render()},{value})"


def _comparison_variables(comparison: BodyComparison) -> tuple[str, ...]:
    """Return unique source variables in stable first-occurrence order."""

    operands = [comparison.left]
    if isinstance(comparison.right, ApplicationOperand):
        operands.append(comparison.right)
    variables = sorted(
        (
            argument
            for operand in operands
            for argument in operand.application.arguments
            if isinstance(argument, VariableTerm)
        ),
        key=lambda argument: argument.span.start,
    )
    seen: set[str] = set()
    result: list[str] = []
    for variable in variables:
        if variable.name in seen:
            continue
        seen.add(variable.name)
        result.append(variable.name)
    return tuple(result)


def _render_helper_atom(name: str, variables: tuple[str, ...]) -> str:
    if not variables:
        return name
    return f"{name}({','.join(variables)})"
