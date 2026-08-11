"""Validate typed research IR and emit grounder-safe theory atoms."""

from __future__ import annotations

from collections.abc import Iterable

from research.native_backend.ir import (
    AssignmentHead,
    Atom,
    AtomHead,
    NativeProgram,
    NativeRule,
    Seed,
    nvariables_in_expression,
    raise_at,
    variables_in_application,
    variables_in_atom,
    variables_in_expression,
    variables_in_term,
)
from research.native_backend.nloops import analyze_nloops

THEORY_DEFINITION = """#theory aspf_native {
    term { - : 0, unary };
    &aspf_native_seed/0 : term, any;
    &aspf_native_rule/0 : term, any;
    &aspf_native_guard/0 : term, any
}.
"""


def _body(atoms: tuple[Atom, ...]) -> str:
    rendered = [atom.render() for atom in atoms]
    return ", ".join(rendered)


def _variables_in_rule(rule: NativeRule) -> set[str]:
    variables: set[str] = set()
    if isinstance(rule.head, AssignmentHead):
        variables.update(variables_in_application(rule.head.application))
        variables.update(variables_in_expression(rule.head.value))
    else:
        variables.update(variables_in_atom(rule.head.atom))
    for definition in rule.definitions:
        variables.update(variables_in_expression(definition.expression))
    for comparison in rule.comparisons:
        variables.update(variables_in_expression(comparison.left))
        variables.update(variables_in_expression(comparison.right))
    return variables


def _rule_meta(rule: NativeRule) -> str:
    variables = sorted(_variables_in_rule(rule))
    suffix = "".join(f",{variable}" for variable in variables)
    return f"meta({rule.identifier}{suffix})"


def _validate_seed(seed: Seed) -> None:
    used = variables_in_application(seed.application) | variables_in_term(seed.value)
    bound = set().union(*(variables_in_atom(atom) for atom in seed.when))
    missing = sorted(used - bound)
    if missing:
        raise_at(
            f"ordinary variable {missing[0]} is not bound by the seed's ordinary body",
            seed.location,
        )


def _cycle(graph: dict[str, set[str]]) -> tuple[str, ...] | None:
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(node: str) -> tuple[str, ...] | None:
        if node in visiting:
            start = visiting.index(node)
            return (*visiting[start:], node)
        if node in visited:
            return None
        visiting.append(node)
        for dependency in sorted(graph.get(node, set())):
            found = visit(dependency)
            if found is not None:
                return found
        visiting.pop()
        visited.add(node)
        return None

    for node in sorted(graph):
        found = visit(node)
        if found is not None:
            return found
    return None


def _validate_rule(rule: NativeRule) -> None:
    body_variables = set().union(*(variables_in_atom(atom) for atom in rule.when))
    missing_variables = sorted(_variables_in_rule(rule) - body_variables)
    if missing_variables:
        raise_at(
            f"ordinary variable {missing_variables[0]} is not bound by the rule's ordinary body",
            rule.location,
        )

    definitions: dict[str, set[str]] = {}
    referenced: set[str] = set()
    for definition in rule.definitions:
        name = definition.variable.name
        dependencies = nvariables_in_expression(definition.expression)
        definitions.setdefault(name, set()).update(dependencies)
        referenced.add(name)
        referenced.update(dependencies)
    if isinstance(rule.head, AssignmentHead):
        referenced.update(nvariables_in_expression(rule.head.value))
    for comparison in rule.comparisons:
        referenced.update(nvariables_in_expression(comparison.left))
        referenced.update(nvariables_in_expression(comparison.right))

    missing_definitions = sorted(referenced - definitions.keys())
    if missing_definitions:
        raise_at(
            f"non-Herbrand variable _{missing_definitions[0]} has no positive definition",
            rule.location,
        )
    found_cycle = _cycle(definitions)
    if found_cycle is not None:
        rendered = " -> ".join(f"_{name}" for name in found_cycle)
        raise_at(f"non-Herbrand definitions are not n-stratified: {rendered}", rule.location)


def validate(program: NativeProgram) -> None:
    """Enforce safety, n-stratification, and the typed positive n-loop screen."""

    for fact in program.facts:
        variables = variables_in_atom(fact)
        if variables:
            raise ValueError(f"research fact contains variable {sorted(variables)[0]}")
    for seed in program.seeds:
        _validate_seed(seed)
    identifiers: set[str] = set()
    for rule in program.rules:
        if rule.identifier in identifiers:
            raise_at(f"duplicate native rule identifier: {rule.identifier}", rule.location)
        identifiers.add(rule.identifier)
        _validate_rule(rule)

    analysis = analyze_nloops(program)
    if analysis.loop is not None:
        loop = analysis.loop
        path = " -> ".join(node.label for node in loop.path)
        shared = ", ".join(
            application.function
            if not application.arguments
            else application.function
            + "("
            + ",".join(argument.render() for argument in application.arguments)
            + ")"
            for application in loop.shared_terms
        )
        raise_at(
            "historical n-loop rejected: positive dependency path "
            f"{path} shares simple term {shared}",
            loop.seed.location,
        )


def _emit_seed(seed: Seed) -> str:
    descriptor = f"assignment({seed.application.encode()},{seed.value.encode_value()})"
    body = _body(seed.when)
    suffix = f" :- {body}" if body else ""
    return f"&aspf_native_seed {{ {descriptor} }}{suffix}."


def _emit_rule(rule: NativeRule) -> list[str]:
    meta = _rule_meta(rule)
    elements = [meta, rule.head.encode()]
    elements.extend(definition.encode() for definition in rule.definitions)
    elements.extend(comparison.encode() for comparison in rule.comparisons)
    descriptor = "; ".join(elements)
    body = _body(rule.when)
    suffix = f" :- {body}" if body else ""
    lines = [f"&aspf_native_rule {{ {descriptor} }}{suffix}."]
    if isinstance(rule.head, AtomHead):
        guard_body = f"{body}, " if body else ""
        guard = f"&aspf_native_guard {{ {meta} }}"
        lines.append(f"{guard} :- {guard_body}not not {guard}.")
        atom_body = f"{body}, " if body else ""
        lines.append(f"{rule.head.atom.render()} :- {atom_body}{guard}.")
    return lines


def compile_program(program: NativeProgram) -> str:
    """Compile validated typed IR to an internal Clingo theory program."""

    validate(program)
    lines = [THEORY_DEFINITION.rstrip()]
    lines.extend(f"{fact.render()}." for fact in program.facts)
    lines.extend(choice.render() for choice in program.choices)
    lines.extend(_emit_seed(seed) for seed in program.seeds)
    lines.extend(line for rule in program.rules for line in _emit_rule(rule))
    return "\n".join(lines) + "\n"


def emitted_identifiers() -> Iterable[str]:
    """Expose the isolated private theory names for collision audits."""

    return ("aspf_native_seed", "aspf_native_rule", "aspf_native_guard")
