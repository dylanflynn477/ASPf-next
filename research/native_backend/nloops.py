"""Typed positive-dependency analysis for historical ASP{f} n-loops.

The historical criterion is defined on a ground program.  This module is exact for
the variable-free portion of the research IR.  For non-ground ordinary terms it
connects unifiable literal patterns, conservatively representing dependencies that
can occur after grounding.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from research.native_backend.ir import (
    AppExpression,
    Application,
    AssignmentHead,
    Atom,
    Comparison,
    ComparisonOperator,
    ConstantExpression,
    Expression,
    GroundTerm,
    NativeProgram,
    NVariableExpression,
    SourceLocation,
    Term,
    Variable,
    applications_in_expression,
    variables_in_application,
    variables_in_atom,
)


class DependencyNodeKind(StrEnum):
    """Literal categories represented in the positive dependency graph."""

    ORDINARY = "ordinary"
    SEED_NATOM = "seed-n-atom"
    DEPENDENT_NATOM = "dependent-n-atom"


class DependencyEdgeKind(StrEnum):
    """Why two literal occurrences are connected."""

    POSITIVE_BODY = "positive-body"
    LITERAL_MATCH = "literal-match"


@dataclass(frozen=True, slots=True)
class DependencyNode:
    """One source literal occurrence with provenance and simple-term metadata."""

    identifier: int
    kind: DependencyNodeKind
    label: str
    simple_terms: tuple[Application, ...]
    location: SourceLocation
    rule_identifier: str
    ordinary_atom: Atom | None = None
    seed_application: Application | None = None
    seed_value: Expression | None = None


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """A deterministic graph edge between literal occurrences."""

    source: int
    target: int
    kind: DependencyEdgeKind
    location: SourceLocation
    rule_identifier: str


@dataclass(frozen=True, slots=True)
class NLoop:
    """A positive path witnessing the historical n-loop criterion."""

    seed: DependencyNode
    endpoint: DependencyNode
    shared_terms: tuple[Application, ...]
    path: tuple[DependencyNode, ...]
    edges: tuple[DependencyEdge, ...]


@dataclass(frozen=True, slots=True)
class NLoopAnalysis:
    """Graph, contract, and first deterministic n-loop witness."""

    nodes: tuple[DependencyNode, ...]
    edges: tuple[DependencyEdge, ...]
    exact_for_ground_program: bool
    loop: NLoop | None


def _render_application(application: Application) -> str:
    if not application.arguments:
        return application.function
    arguments = ",".join(argument.render() for argument in application.arguments)
    return f"{application.function}({arguments})"


def _render_expression(expression: Expression) -> str:
    if isinstance(expression, ConstantExpression):
        return expression.value.render()
    if isinstance(expression, AppExpression):
        return _render_application(expression.application)
    return f"_{expression.variable.name}"


def _render_comparison(comparison: Comparison) -> str:
    operators = {
        ComparisonOperator.EQUAL: "#=",
        ComparisonOperator.NOT_EQUAL: "#!=",
        ComparisonOperator.LESS: "#<",
        ComparisonOperator.LESS_EQUAL: "#<=",
        ComparisonOperator.GREATER: "#>",
        ComparisonOperator.GREATER_EQUAL: "#>=",
    }
    return (
        f"{_render_expression(comparison.left)}"
        f"{operators[comparison.operator]}"
        f"{_render_expression(comparison.right)}"
    )


_VariableKey = tuple[str, str]


def _term_pairs_unifiable(
    pairs: tuple[tuple[Term, Term], ...],
    left_scope: str,
    right_scope: str,
) -> bool:
    """Decide pairwise first-order unifiability with occurrence-local variables.

    Variable names are shared across occurrences from the same source rule and kept
    distinct across rules.  Retaining those equality constraints avoids false matches
    such as ``p(X,X)`` with ``p(a,b)`` while remaining independent of value-domain
    enumeration.
    """

    edges: dict[_VariableKey, set[_VariableKey]] = {}
    constants: dict[_VariableKey, set[GroundTerm]] = {}

    def variable_key(scope: str, term: Variable) -> _VariableKey:
        key = (scope, term.name)
        edges.setdefault(key, set())
        constants.setdefault(key, set())
        return key

    for left, right in pairs:
        if isinstance(left, Variable) and isinstance(right, Variable):
            left_key = variable_key(left_scope, left)
            right_key = variable_key(right_scope, right)
            edges[left_key].add(right_key)
            edges[right_key].add(left_key)
        elif isinstance(left, Variable):
            constants[variable_key(left_scope, left)].add(cast(GroundTerm, right))
        elif isinstance(right, Variable):
            constants[variable_key(right_scope, right)].add(left)
        elif left != right:
            return False

    visited: set[_VariableKey] = set()
    for start in sorted(edges):
        if start in visited:
            continue
        pending = [start]
        component_constants: set[GroundTerm] = set()
        while pending:
            key = pending.pop()
            if key in visited:
                continue
            visited.add(key)
            component_constants.update(constants[key])
            pending.extend(edges[key] - visited)
        if len(component_constants) > 1:
            return False
    return True


def _applications_compatible(
    left: Application,
    right: Application,
    left_scope: str,
    right_scope: str,
) -> bool:
    return (
        left.function == right.function
        and len(left.arguments) == len(right.arguments)
        and _term_pairs_unifiable(
            tuple(zip(left.arguments, right.arguments, strict=True)),
            left_scope,
            right_scope,
        )
    )


def _atoms_compatible(
    left: Atom,
    right: Atom,
    left_scope: str,
    right_scope: str,
) -> bool:
    return (
        left.name == right.name
        and len(left.arguments) == len(right.arguments)
        and _term_pairs_unifiable(
            tuple(zip(left.arguments, right.arguments, strict=True)),
            left_scope,
            right_scope,
        )
    )


def _natoms_compatible(left: DependencyNode, right: DependencyNode) -> bool:
    if (
        left.seed_application is None
        or left.seed_value is None
        or right.seed_application is None
        or right.seed_value is None
    ):
        return False
    left_application = left.seed_application
    right_application = right.seed_application
    if left_application.function != right_application.function or len(
        left_application.arguments
    ) != len(right_application.arguments):
        return False
    pairs = list(zip(left_application.arguments, right_application.arguments, strict=True))
    left_value = left.seed_value
    right_value = right.seed_value
    if isinstance(left_value, NVariableExpression) or isinstance(right_value, NVariableExpression):
        pass
    elif isinstance(left_value, ConstantExpression) and isinstance(right_value, ConstantExpression):
        pairs.append((left_value.value, right_value.value))
    elif isinstance(left_value, AppExpression) and isinstance(right_value, AppExpression):
        left_nested = left_value.application
        right_nested = right_value.application
        if left_nested.function != right_nested.function or len(left_nested.arguments) != len(
            right_nested.arguments
        ):
            return False
        pairs.extend(zip(left_nested.arguments, right_nested.arguments, strict=True))
    else:
        return False
    return _term_pairs_unifiable(
        tuple(pairs),
        left.rule_identifier,
        right.rule_identifier,
    )


def _nodes_match(left: DependencyNode, right: DependencyNode) -> bool:
    if left.ordinary_atom is not None and right.ordinary_atom is not None:
        return _atoms_compatible(
            left.ordinary_atom,
            right.ordinary_atom,
            left.rule_identifier,
            right.rule_identifier,
        )
    return _natoms_compatible(left, right)


def _seed_parts(comparison: Comparison) -> tuple[Application, Expression] | None:
    if comparison.operator is not ComparisonOperator.EQUAL:
        return None
    if isinstance(comparison.left, AppExpression) and isinstance(
        comparison.right, ConstantExpression
    ):
        return comparison.left.application, comparison.right
    if isinstance(comparison.right, AppExpression) and isinstance(
        comparison.left, ConstantExpression
    ):
        return comparison.right.application, comparison.left
    return None


def _shared_terms(seed: DependencyNode, endpoint: DependencyNode) -> tuple[Application, ...]:
    shared = {
        seed_term
        for seed_term in seed.simple_terms
        if any(
            _applications_compatible(
                seed_term,
                endpoint_term,
                seed.rule_identifier,
                endpoint.rule_identifier,
            )
            for endpoint_term in endpoint.simple_terms
        )
    }
    return tuple(sorted(shared, key=_render_application))


def _find_loop(
    nodes: tuple[DependencyNode, ...],
    edges: tuple[DependencyEdge, ...],
    seed_identifiers: tuple[int, ...],
) -> NLoop | None:
    by_id = {node.identifier: node for node in nodes}
    outgoing: dict[int, list[DependencyEdge]] = {}
    for edge in edges:
        outgoing.setdefault(edge.source, []).append(edge)
    for candidates in outgoing.values():
        candidates.sort(key=lambda edge: (edge.target, edge.kind.value))

    for seed_identifier in seed_identifiers:
        seed = by_id[seed_identifier]
        start = (seed_identifier, False)
        pending = deque([start])
        visited = {start}
        parent: dict[tuple[int, bool], tuple[tuple[int, bool], DependencyEdge]] = {}
        while pending:
            state = pending.popleft()
            identifier, has_positive_edge = state
            node = by_id[identifier]
            shared = _shared_terms(seed, node) if has_positive_edge else ()
            if shared and node.kind is not DependencyNodeKind.ORDINARY:
                states = [state]
                path_edges: list[DependencyEdge] = []
                while states[-1] != start:
                    previous, edge = parent[states[-1]]
                    path_edges.append(edge)
                    states.append(previous)
                states.reverse()
                path_edges.reverse()
                return NLoop(
                    seed=seed,
                    endpoint=node,
                    shared_terms=shared,
                    path=tuple(by_id[path_state[0]] for path_state in states),
                    edges=tuple(path_edges),
                )
            for edge in outgoing.get(identifier, ()):
                next_state = (
                    edge.target,
                    has_positive_edge or edge.kind is DependencyEdgeKind.POSITIVE_BODY,
                )
                if next_state not in visited:
                    visited.add(next_state)
                    parent[next_state] = (state, edge)
                    pending.append(next_state)
    return None


def analyze_nloops(program: NativeProgram) -> NLoopAnalysis:
    """Build the positive graph and return the first historical n-loop witness.

    Literal matching is equality for variable-free programs and conservative
    unification for ordinary-variable patterns.  Match edges represent occurrence
    identity and do not themselves make a positive path nonempty.
    """

    nodes: list[DependencyNode] = []
    edges: list[DependencyEdge] = []
    seed_identifiers: list[int] = []
    exact = True

    def add_node(
        kind: DependencyNodeKind,
        label: str,
        simple_terms: tuple[Application, ...],
        location: SourceLocation,
        rule_identifier: str,
        *,
        ordinary_atom: Atom | None = None,
        seed_application: Application | None = None,
        seed_value: Expression | None = None,
    ) -> int:
        identifier = len(nodes)
        nodes.append(
            DependencyNode(
                identifier,
                kind,
                label,
                simple_terms,
                location,
                rule_identifier,
                ordinary_atom,
                seed_application,
                seed_value,
            )
        )
        return identifier

    def add_positive_edges(
        head: int,
        body: list[int],
        location: SourceLocation,
        rule_identifier: str,
    ) -> None:
        edges.extend(
            DependencyEdge(
                head,
                target,
                DependencyEdgeKind.POSITIVE_BODY,
                location,
                rule_identifier,
            )
            for target in body
        )

    for index, seed in enumerate(program.seeds):
        value = ConstantExpression(seed.value)
        head = add_node(
            DependencyNodeKind.SEED_NATOM,
            f"{_render_application(seed.application)}#={seed.value.render()}",
            (seed.application,),
            seed.location,
            f"seed[{index}]",
            seed_application=seed.application,
            seed_value=value,
        )
        seed_identifiers.append(head)
        seed_body = [
            add_node(
                DependencyNodeKind.ORDINARY,
                atom.render(),
                (),
                seed.location,
                f"seed[{index}]",
                ordinary_atom=atom,
            )
            for atom in seed.when
        ]
        add_positive_edges(head, seed_body, seed.location, f"seed[{index}]")
        exact = exact and not variables_in_application(seed.application)
        exact = exact and all(not variables_in_atom(atom) for atom in seed.when)
        exact = exact and not isinstance(seed.value, Variable)

    for rule in program.rules:
        if isinstance(rule.head, AssignmentHead):
            head = add_node(
                DependencyNodeKind.SEED_NATOM,
                (
                    f"{_render_application(rule.head.application)}"
                    f"#={_render_expression(rule.head.value)}"
                ),
                (rule.head.application,),
                rule.location,
                rule.identifier,
                seed_application=rule.head.application,
                seed_value=rule.head.value,
            )
            seed_identifiers.append(head)
            exact = exact and not variables_in_application(rule.head.application)
            exact = exact and isinstance(rule.head.value, ConstantExpression)
        else:
            head = add_node(
                DependencyNodeKind.ORDINARY,
                rule.head.atom.render(),
                (),
                rule.location,
                rule.identifier,
                ordinary_atom=rule.head.atom,
            )
            exact = exact and not variables_in_atom(rule.head.atom)

        rule_body_nodes: list[int] = []
        for atom in rule.when:
            rule_body_nodes.append(
                add_node(
                    DependencyNodeKind.ORDINARY,
                    atom.render(),
                    (),
                    rule.location,
                    rule.identifier,
                    ordinary_atom=atom,
                )
            )
            exact = exact and not variables_in_atom(atom)
        for definition in rule.definitions:
            applications = tuple(
                sorted(
                    applications_in_expression(definition.expression),
                    key=_render_application,
                )
            )
            definition_application = (
                definition.expression.application
                if isinstance(definition.expression, AppExpression)
                else None
            )
            exact = exact and definition_application is None
            rule_body_nodes.append(
                add_node(
                    DependencyNodeKind.DEPENDENT_NATOM,
                    f"_{definition.variable.name}#={_render_expression(definition.expression)}",
                    applications,
                    rule.location,
                    rule.identifier,
                    seed_application=definition_application,
                    seed_value=(
                        NVariableExpression(definition.variable)
                        if definition_application is not None
                        else None
                    ),
                )
            )
            exact = exact and all(
                not variables_in_application(application) for application in applications
            )
        for comparison in rule.comparisons:
            if comparison.default_negated:
                continue
            applications = tuple(
                sorted(
                    (
                        *applications_in_expression(comparison.left),
                        *applications_in_expression(comparison.right),
                    ),
                    key=_render_application,
                )
            )
            seed_parts = _seed_parts(comparison)
            rule_body_nodes.append(
                add_node(
                    (
                        DependencyNodeKind.SEED_NATOM
                        if seed_parts is not None
                        else DependencyNodeKind.DEPENDENT_NATOM
                    ),
                    _render_comparison(comparison),
                    applications,
                    rule.location,
                    rule.identifier,
                    seed_application=None if seed_parts is None else seed_parts[0],
                    seed_value=None if seed_parts is None else seed_parts[1],
                )
            )
            exact = exact and all(
                not variables_in_application(application) for application in applications
            )
        add_positive_edges(head, rule_body_nodes, rule.location, rule.identifier)

    for left_index, left in enumerate(nodes):
        for right in nodes[left_index + 1 :]:
            if not _nodes_match(left, right):
                continue
            for source, target in ((left, right), (right, left)):
                edges.append(
                    DependencyEdge(
                        source.identifier,
                        target.identifier,
                        DependencyEdgeKind.LITERAL_MATCH,
                        source.location,
                        source.rule_identifier,
                    )
                )

    graph_nodes = tuple(nodes)
    graph_edges = tuple(sorted(edges, key=lambda edge: (edge.source, edge.target, edge.kind.value)))
    return NLoopAnalysis(
        nodes=graph_nodes,
        edges=graph_edges,
        exact_for_ground_program=exact,
        loop=_find_loop(graph_nodes, graph_edges, tuple(seed_identifiers)),
    )
