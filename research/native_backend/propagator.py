"""Thread-scoped solver state for the native-backend feasibility prototype."""

from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import Enum, StrEnum
from heapq import heapify, heappop, heappush
from typing import TypeAlias

import clingo


class ValueKind(StrEnum):
    """Kinds retained when reconstructing ASP{f} values."""

    INTEGER = "integer"
    SYMBOL = "symbol"
    STRING = "string"


@dataclass(frozen=True, slots=True, order=True)
class GroundValue:
    """A typed, ground solver-time value."""

    kind: ValueKind
    payload: int | str

    def render(self) -> str:
        if self.kind is ValueKind.STRING:
            return json.dumps(self.payload, ensure_ascii=False)
        return str(self.payload)


@dataclass(frozen=True, slots=True, order=True)
class GroundApplication:
    """A ground non-Herbrand application key."""

    function: str
    arguments: tuple[GroundValue, ...]

    def render(self) -> str:
        if not self.arguments:
            return self.function
        rendered = ",".join(argument.render() for argument in self.arguments)
        return f"{self.function}({rendered})"


@dataclass(frozen=True, slots=True)
class ConstantGroundExpression:
    value: GroundValue


@dataclass(frozen=True, slots=True)
class ApplicationGroundExpression:
    application: GroundApplication


@dataclass(frozen=True, slots=True)
class NVariableGroundExpression:
    name: str


GroundExpression: TypeAlias = (
    ConstantGroundExpression | ApplicationGroundExpression | NVariableGroundExpression
)


@dataclass(frozen=True, slots=True)
class GroundDefinition:
    variable: str
    expression: GroundExpression


class GroundComparisonOperator(Enum):
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    LESS = "lt"
    LESS_EQUAL = "le"
    GREATER = "gt"
    GREATER_EQUAL = "ge"


@dataclass(frozen=True, slots=True)
class GroundComparison:
    left: GroundExpression
    operator: GroundComparisonOperator
    right: GroundExpression
    default_negated: bool


@dataclass(frozen=True, slots=True)
class GroundAssignmentHead:
    application: GroundApplication
    expression: GroundExpression


@dataclass(frozen=True, slots=True)
class GroundAtomHead:
    rendered: str


GroundHead: TypeAlias = GroundAssignmentHead | GroundAtomHead


@dataclass(frozen=True, slots=True, order=True)
class RuleKey:
    identifier: str
    instance: tuple[GroundValue, ...]


@dataclass(frozen=True, slots=True)
class GroundRule:
    key: RuleKey
    head: GroundHead
    definitions: tuple[GroundDefinition, ...]
    comparisons: tuple[GroundComparison, ...]
    active_literal: int
    guard_literal: int | None = None


@dataclass(frozen=True, slots=True)
class GroundSeed:
    application: GroundApplication
    value: GroundValue
    literal: int


class StateKind(StrEnum):
    """Explicit state; undefinedness is not represented as a source value."""

    UNDEFINED = "undefined"
    DEFINED = "defined"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class ValueState:
    kind: StateKind
    value: GroundValue | None = None
    explanation: frozenset[int] | None = None


UNDEFINED = ValueState(StateKind.UNDEFINED)


Explanation: TypeAlias = frozenset[int]
ApplicationValues: TypeAlias = dict[GroundApplication, dict[GroundValue, Explanation | None]]


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    """A rule-body result and the solver literals sufficient to justify it."""

    satisfied: bool
    nvariables: dict[str, ValueState]
    explanation: Explanation | None
    explanation_gap: str | None = None


@dataclass(frozen=True, slots=True)
class NativeSnapshot:
    """Valid native state associated with one Clingo solving thread."""

    ordinary_atoms: tuple[str, ...]
    assignments: tuple[tuple[GroundApplication, GroundValue], ...]
    undefined_nvariables: tuple[tuple[RuleKey, str], ...]


@dataclass(frozen=True, slots=True)
class NativeWorkMetrics:
    """Deterministic counters for profiling propagator work."""

    theory_atoms: int
    seeds: int
    rules: int
    application_decode_requests: int
    decoded_applications: int
    application_cache_hits: int
    value_decode_requests: int
    decoded_values: int
    value_cache_hits: int
    watched_literals: int
    ordinary_atoms: int
    ordinary_watched_literals: int
    ordinary_activations: int
    ordinary_deactivations: int
    propagate_calls: int
    propagated_literals: int
    seed_activations: int
    seed_deactivations: int
    check_calls: int
    check_seed_probes: int
    rule_body_evaluations: int
    blocking_clauses: int
    functionality_clauses: int
    derived_functionality_clauses: int
    guard_clauses: int
    narrow_blocking_clauses: int
    broad_blocking_clauses: int
    broad_clause_causes: tuple[tuple[str, int], ...]
    duplicate_clauses: int
    clause_add_conflicts: int
    clause_propagations: int
    early_explanation_clauses: int
    clause_literals: int
    maximum_clause_width: int
    snapshot_assignments: int
    undo_calls: int
    undone_literals: int


@dataclass(slots=True)
class _ThreadState:
    """Assignment-dependent state owned by one Clingo solving thread."""

    true_literals: set[int]
    seed_supports: dict[GroundApplication, dict[GroundValue, dict[int, int]]]
    ordinary_supports: dict[str, int]


@dataclass(slots=True)
class _EvaluationState:
    """One deterministic native closure over a thread's current positive supports."""

    applications: ApplicationValues
    active: tuple[bool, ...]
    rule_states: dict[int, dict[str, ValueState]]
    rule_satisfaction: dict[int, bool]
    rule_explanations: dict[int, Explanation | None]
    rule_explanation_gaps: dict[int, str | None]


def _expect_function(term: clingo.TheoryTerm, name: str, arity: int | None = None) -> None:
    if term.type is not clingo.TheoryTermType.Function or term.name != name:
        raise RuntimeError(f"invalid native theory term: expected {name}, got {term}")
    if arity is not None and len(term.arguments) != arity:
        raise RuntimeError(f"invalid native theory arity for {name}: {term}")


def _decode_integer_term(term: clingo.TheoryTerm) -> int:
    if term.type is clingo.TheoryTermType.Number:
        return term.number
    if (
        term.type is clingo.TheoryTermType.Function
        and term.name == "-"
        and len(term.arguments) == 1
    ):
        return -_decode_integer_term(term.arguments[0])
    raise RuntimeError(f"invalid integer theory term: {term}")


def _decode_raw_value(term: clingo.TheoryTerm) -> GroundValue:
    if term.type is clingo.TheoryTermType.Number:
        return GroundValue(ValueKind.INTEGER, term.number)
    if term.type is clingo.TheoryTermType.Symbol:
        if term.name.startswith('"'):
            loaded = json.loads(term.name)
            if not isinstance(loaded, str):
                raise RuntimeError(f"invalid string theory term: {term}")
            return GroundValue(ValueKind.STRING, loaded)
        return GroundValue(ValueKind.SYMBOL, term.name)
    if term.type is clingo.TheoryTermType.Function and term.name == "-":
        return GroundValue(ValueKind.INTEGER, _decode_integer_term(term))
    raise RuntimeError(f"unsupported ground theory value: {term}")


def _decode_value(term: clingo.TheoryTerm) -> GroundValue:
    if term.type is not clingo.TheoryTermType.Function or len(term.arguments) != 1:
        raise RuntimeError(f"invalid encoded value: {term}")
    argument = term.arguments[0]
    if term.name == "integer":
        return GroundValue(ValueKind.INTEGER, _decode_integer_term(argument))
    if term.name == "symbol":
        value = _decode_raw_value(argument)
        if value.kind is not ValueKind.SYMBOL:
            raise RuntimeError(f"invalid symbolic value: {term}")
        return value
    if term.name == "string":
        value = _decode_raw_value(argument)
        if value.kind is not ValueKind.STRING:
            raise RuntimeError(f"invalid string value: {term}")
        return value
    if term.name == "ordinary":
        return _decode_raw_value(argument)
    raise RuntimeError(f"invalid value wrapper: {term}")


def _decode_application(term: clingo.TheoryTerm) -> GroundApplication:
    _expect_function(term, "app")
    if not term.arguments:
        raise RuntimeError(f"application lacks a function: {term}")
    function_term = term.arguments[0]
    if function_term.type is not clingo.TheoryTermType.Symbol:
        raise RuntimeError(f"invalid application function: {term}")
    return GroundApplication(
        function_term.name,
        tuple(_decode_raw_value(argument) for argument in term.arguments[1:]),
    )


def _decode_nvariable(term: clingo.TheoryTerm) -> str:
    _expect_function(term, "nvar", 1)
    name = term.arguments[0]
    if name.type is not clingo.TheoryTermType.Symbol:
        raise RuntimeError(f"invalid n-variable metadata: {term}")
    return name.name


class _TheoryDecoder:
    """Initialization-local canonicalization for interned Clingo theory terms."""

    def __init__(self) -> None:
        self.applications: dict[clingo.TheoryTerm, GroundApplication] = {}
        self.values: dict[clingo.TheoryTerm, GroundValue] = {}
        self.application_requests = 0
        self.application_cache_hits = 0
        self.value_requests = 0
        self.value_cache_hits = 0

    def application(self, term: clingo.TheoryTerm) -> GroundApplication:
        self.application_requests += 1
        cached = self.applications.get(term)
        if cached is not None:
            self.application_cache_hits += 1
            return cached
        decoded = _decode_application(term)
        self.applications[term] = decoded
        return decoded

    def value(self, term: clingo.TheoryTerm) -> GroundValue:
        self.value_requests += 1
        cached = self.values.get(term)
        if cached is not None:
            self.value_cache_hits += 1
            return cached
        decoded = _decode_value(term)
        self.values[term] = decoded
        return decoded

    def expression(self, term: clingo.TheoryTerm) -> GroundExpression:
        if term.type is not clingo.TheoryTermType.Function or len(term.arguments) != 1:
            raise RuntimeError(f"invalid native expression: {term}")
        if term.name == "constant":
            return ConstantGroundExpression(self.value(term.arguments[0]))
        if term.name == "application":
            return ApplicationGroundExpression(self.application(term.arguments[0]))
        if term.name == "nvalue":
            return NVariableGroundExpression(_decode_nvariable(term.arguments[0]))
        raise RuntimeError(f"unknown native expression: {term}")


def _decode_meta(term: clingo.TheoryTerm) -> RuleKey:
    _expect_function(term, "meta")
    if not term.arguments or term.arguments[0].type is not clingo.TheoryTermType.Symbol:
        raise RuntimeError(f"invalid native rule metadata: {term}")
    return RuleKey(
        term.arguments[0].name,
        tuple(_decode_raw_value(argument) for argument in term.arguments[1:]),
    )


def _decode_head(term: clingo.TheoryTerm, decoder: _TheoryDecoder) -> GroundHead:
    if term.type is not clingo.TheoryTermType.Function:
        raise RuntimeError(f"invalid native rule head: {term}")
    if term.name == "head_assignment" and len(term.arguments) == 2:
        return GroundAssignmentHead(
            decoder.application(term.arguments[0]),
            decoder.expression(term.arguments[1]),
        )
    if term.name == "head_atom" and len(term.arguments) == 1:
        atom = term.arguments[0]
        _expect_function(atom, "atom")
        if not atom.arguments or atom.arguments[0].type is not clingo.TheoryTermType.Symbol:
            raise RuntimeError(f"invalid ordinary native head: {term}")
        name = atom.arguments[0].name
        arguments = tuple(_decode_raw_value(argument) for argument in atom.arguments[1:])
        rendered = name
        if arguments:
            rendered += f"({','.join(argument.render() for argument in arguments)})"
        return GroundAtomHead(rendered)
    raise RuntimeError(f"unknown native rule head: {term}")


def _decode_definition(term: clingo.TheoryTerm, decoder: _TheoryDecoder) -> GroundDefinition:
    _expect_function(term, "define", 2)
    return GroundDefinition(
        _decode_nvariable(term.arguments[0]),
        decoder.expression(term.arguments[1]),
    )


def _decode_comparison(term: clingo.TheoryTerm, decoder: _TheoryDecoder) -> GroundComparison:
    _expect_function(term, "compare", 4)
    operator_term, polarity_term, left_term, right_term = term.arguments
    if (
        operator_term.type is not clingo.TheoryTermType.Symbol
        or polarity_term.type is not clingo.TheoryTermType.Symbol
    ):
        raise RuntimeError(f"invalid native comparison: {term}")
    return GroundComparison(
        decoder.expression(left_term),
        GroundComparisonOperator(operator_term.name),
        decoder.expression(right_term),
        polarity_term.name == "default_negated",
    )


def _element_terms(atom: clingo.TheoryAtom) -> tuple[clingo.TheoryTerm, ...]:
    terms: list[clingo.TheoryTerm] = []
    for element in atom.elements:
        if element.condition:
            raise RuntimeError(f"conditional element is not valid native metadata: {element}")
        if len(element.terms) != 1:
            raise RuntimeError(f"invalid native metadata element: {element}")
        terms.append(element.terms[0])
    return tuple(terms)


def _decode_seed(atom: clingo.TheoryAtom, literal: int, decoder: _TheoryDecoder) -> GroundSeed:
    terms = _element_terms(atom)
    if len(terms) != 1:
        raise RuntimeError(f"invalid native seed: {atom}")
    assignment = terms[0]
    _expect_function(assignment, "assignment", 2)
    return GroundSeed(
        decoder.application(assignment.arguments[0]),
        decoder.value(assignment.arguments[1]),
        literal,
    )


def _decode_rule(atom: clingo.TheoryAtom, literal: int, decoder: _TheoryDecoder) -> GroundRule:
    terms = _element_terms(atom)
    if len(terms) < 2:
        raise RuntimeError(f"native rule lacks metadata or head: {atom}")
    metadata = tuple(term for term in terms if term.name == "meta")
    heads = tuple(term for term in terms if term.name in {"head_assignment", "head_atom"})
    if len(metadata) != 1 or len(heads) != 1:
        raise RuntimeError(f"native rule has ambiguous metadata or head: {atom}")
    definitions = tuple(
        _decode_definition(term, decoder) for term in terms if term.name == "define"
    )
    comparisons = tuple(
        _decode_comparison(term, decoder) for term in terms if term.name == "compare"
    )
    return GroundRule(
        key=_decode_meta(metadata[0]),
        head=_decode_head(heads[0], decoder),
        definitions=definitions,
        comparisons=comparisons,
        active_literal=literal,
    )


def _decode_guard(atom: clingo.TheoryAtom, literal: int) -> tuple[RuleKey, int]:
    terms = _element_terms(atom)
    if len(terms) != 1:
        raise RuntimeError(f"invalid native guard: {atom}")
    return _decode_meta(terms[0]), literal


def _merge_explanations(explanations: Iterable[Explanation | None]) -> Explanation | None:
    """Combine conjunctive supports, preserving an unknown explanation as unknown."""

    merged: set[int] = set()
    for explanation in explanations:
        if explanation is None:
            return None
        merged.update(explanation)
    return frozenset(merged)


def _prefer_explanation(candidate: Explanation | None, current: Explanation | None) -> bool:
    """Choose a deterministic small support when one value has several derivations."""

    if candidate is None:
        return False
    if current is None:
        return True
    return (len(candidate), tuple(sorted(candidate))) < (len(current), tuple(sorted(current)))


def _application_state(
    values: ApplicationValues,
    application: GroundApplication,
    potential_applications: frozenset[GroundApplication],
) -> ValueState:
    candidates = values.get(application, {})
    if not candidates:
        explanation: Explanation | None = None
        if application not in potential_applications:
            explanation = frozenset()
        return ValueState(StateKind.UNDEFINED, explanation=explanation)
    if len(candidates) > 1:
        first, second = sorted(candidates)[:2]
        explanation = _merge_explanations((candidates[first], candidates[second]))
        return ValueState(StateKind.CONFLICT, explanation=explanation)
    value, explanation = next(iter(candidates.items()))
    return ValueState(StateKind.DEFINED, value, explanation)


def _evaluate_expression(
    expression: GroundExpression,
    applications: ApplicationValues,
    nvariables: dict[str, ValueState],
    potential_applications: frozenset[GroundApplication],
) -> ValueState:
    if isinstance(expression, ConstantGroundExpression):
        return ValueState(StateKind.DEFINED, expression.value, frozenset())
    if isinstance(expression, ApplicationGroundExpression):
        return _application_state(
            applications,
            expression.application,
            potential_applications,
        )
    return nvariables.get(expression.name, UNDEFINED)


def _resolve_nvariables(
    rule: GroundRule,
    applications: ApplicationValues,
    potential_applications: frozenset[GroundApplication],
) -> dict[str, ValueState]:
    grouped: dict[str, list[GroundExpression]] = {}
    for definition in rule.definitions:
        grouped.setdefault(definition.variable, []).append(definition.expression)
    resolved: dict[str, ValueState] = {}
    pending = dict(grouped)
    while pending:
        progressed = False
        for name, expressions in tuple(pending.items()):
            dependencies = {
                expression.name
                for expression in expressions
                if isinstance(expression, NVariableGroundExpression)
            }
            if not dependencies.issubset(resolved):
                continue
            states = [
                _evaluate_expression(
                    expression,
                    applications,
                    resolved,
                    potential_applications,
                )
                for expression in expressions
            ]
            values = {
                state.value
                for state in states
                if state.kind is StateKind.DEFINED and state.value is not None
            }
            if all(state.kind is StateKind.DEFINED for state in states) and len(values) == 1:
                resolved[name] = ValueState(
                    StateKind.DEFINED,
                    next(iter(values)),
                    _merge_explanations(state.explanation for state in states),
                )
            else:
                known_undefined = next(
                    (
                        state.explanation
                        for state in states
                        if state.kind is not StateKind.DEFINED and state.explanation is not None
                    ),
                    None,
                )
                if known_undefined is None and len(values) > 1:
                    first, second = sorted(values)[:2]
                    conflicting = (
                        state.explanation
                        for value in (first, second)
                        for state in states
                        if state.kind is StateKind.DEFINED and state.value == value
                    )
                    known_undefined = _merge_explanations(conflicting)
                resolved[name] = ValueState(
                    StateKind.UNDEFINED,
                    explanation=known_undefined,
                )
            del pending[name]
            progressed = True
        if not progressed:
            raise RuntimeError(f"decoded rule is not n-stratified: {rule.key.identifier}")
    return resolved


def _compare_values(
    left: GroundValue, operator: GroundComparisonOperator, right: GroundValue
) -> bool:
    if operator is GroundComparisonOperator.EQUAL:
        return left == right
    if operator is GroundComparisonOperator.NOT_EQUAL:
        return left != right
    left_key = (left.kind.value, left.payload)
    right_key = (right.kind.value, right.payload)
    if operator is GroundComparisonOperator.LESS:
        return left_key < right_key
    if operator is GroundComparisonOperator.LESS_EQUAL:
        return left_key <= right_key
    if operator is GroundComparisonOperator.GREATER:
        return left_key > right_key
    return left_key >= right_key


def _rule_body(
    rule: GroundRule,
    applications: ApplicationValues,
    potential_applications: frozenset[GroundApplication],
) -> RuleEvaluation:
    nvariables = _resolve_nvariables(rule, applications, potential_applications)
    satisfied_explanations: list[Explanation | None] = []
    for definition in rule.definitions:
        variable = nvariables[definition.variable]
        expression = _evaluate_expression(
            definition.expression,
            applications,
            nvariables,
            potential_applications,
        )
        if variable.kind is not StateKind.DEFINED:
            gap = None if variable.explanation is not None else f"definition:{definition.variable}"
            return RuleEvaluation(False, nvariables, variable.explanation, gap)
        if expression.kind is not StateKind.DEFINED or expression.value != variable.value:
            gap = None if expression.explanation is not None else "definition-expression"
            return RuleEvaluation(False, nvariables, expression.explanation, gap)
        satisfied_explanations.append(
            _merge_explanations((variable.explanation, expression.explanation))
        )
    for comparison in rule.comparisons:
        left = _evaluate_expression(
            comparison.left,
            applications,
            nvariables,
            potential_applications,
        )
        right = _evaluate_expression(
            comparison.right,
            applications,
            nvariables,
            potential_applications,
        )
        if (
            left.kind is StateKind.DEFINED
            and right.kind is StateKind.DEFINED
            and left.value is not None
            and right.value is not None
        ):
            positive = _compare_values(left.value, comparison.operator, right.value)
            comparison_explanation = _merge_explanations((left.explanation, right.explanation))
        else:
            positive = False
            known_undefined = next(
                (
                    state.explanation
                    for state in (left, right)
                    if state.kind is StateKind.UNDEFINED and state.explanation is not None
                ),
                None,
            )
            comparison_explanation = known_undefined
        satisfied = not positive if comparison.default_negated else positive
        if not satisfied:
            gap = (
                None
                if comparison_explanation is not None
                else f"comparison:{comparison.operator.value}"
            )
            return RuleEvaluation(False, nvariables, comparison_explanation, gap)
        satisfied_explanations.append(comparison_explanation)
    explanation = _merge_explanations(satisfied_explanations)
    return RuleEvaluation(
        True,
        nvariables,
        explanation,
        None if explanation is not None else "satisfied-body",
    )


def _rule_applications(rule: GroundRule) -> set[GroundApplication]:
    """Return application keys whose values can affect a decoded rule."""

    expressions: list[GroundExpression] = [definition.expression for definition in rule.definitions]
    for comparison in rule.comparisons:
        expressions.extend((comparison.left, comparison.right))
    if isinstance(rule.head, GroundAssignmentHead):
        expressions.append(rule.head.expression)
    return {
        expression.application
        for expression in expressions
        if isinstance(expression, ApplicationGroundExpression)
    }


def _rule_dependency_order(rules: tuple[GroundRule, ...]) -> tuple[int, ...]:
    """Order providers before rules that read their derived applications."""

    providers: dict[GroundApplication, list[int]] = {}
    for index, rule in enumerate(rules):
        if isinstance(rule.head, GroundAssignmentHead):
            providers.setdefault(rule.head.application, []).append(index)
    successors = [set[int]() for _rule in rules]
    indegrees = [0 for _rule in rules]
    for consumer, rule in enumerate(rules):
        for application in _rule_applications(rule):
            for provider in providers.get(application, ()):
                if consumer not in successors[provider]:
                    successors[provider].add(consumer)
                    indegrees[consumer] += 1
    ready = [index for index, indegree in enumerate(indegrees) if indegree == 0]
    heapify(ready)
    ordered: list[int] = []
    while ready:
        provider = heappop(ready)
        ordered.append(provider)
        for consumer in sorted(successors[provider]):
            indegrees[consumer] -= 1
            if indegrees[consumer] == 0:
                heappush(ready, consumer)
    if len(ordered) != len(rules):
        ordered.extend(index for index in range(len(rules)) if index not in ordered)
    return tuple(ordered)


def _expression_is_potential(
    expression: GroundExpression,
    applications: set[GroundApplication],
    nvariables: dict[str, bool],
) -> bool:
    if isinstance(expression, ConstantGroundExpression):
        return True
    if isinstance(expression, ApplicationGroundExpression):
        return expression.application in applications
    return nvariables.get(expression.name, False)


def _rule_can_produce_value(
    rule: GroundRule,
    applications: set[GroundApplication],
) -> bool:
    """Over-approximate whether a grounded rule can ever derive its head value.

    The analysis deliberately ignores value equality and comparison outcomes. Its only
    proof-producing result is the negative one: an application outside the fixed point
    has no grounded seed or viable assignment-provider path and is therefore always
    undefined in this compiled program.
    """

    grouped: dict[str, list[GroundExpression]] = {}
    for definition in rule.definitions:
        grouped.setdefault(definition.variable, []).append(definition.expression)
    nvariables: dict[str, bool] = {}
    pending = dict(grouped)
    while pending:
        progressed = False
        for name, expressions in tuple(pending.items()):
            dependencies = {
                expression.name
                for expression in expressions
                if isinstance(expression, NVariableGroundExpression)
            }
            if not dependencies.issubset(nvariables):
                continue
            nvariables[name] = all(
                _expression_is_potential(expression, applications, nvariables)
                for expression in expressions
            )
            del pending[name]
            progressed = True
        if not progressed:
            raise RuntimeError(f"decoded rule is not n-stratified: {rule.key.identifier}")

    if any(not possible for possible in nvariables.values()):
        return False
    for comparison in rule.comparisons:
        if comparison.default_negated:
            continue
        if not _expression_is_potential(
            comparison.left, applications, nvariables
        ) or not _expression_is_potential(comparison.right, applications, nvariables):
            return False
    if not isinstance(rule.head, GroundAssignmentHead):
        return False
    return _expression_is_potential(rule.head.expression, applications, nvariables)


def _potential_applications(
    seeds: tuple[GroundSeed, ...], rules: tuple[GroundRule, ...]
) -> frozenset[GroundApplication]:
    """Compute a sound over-approximation of applications that can become defined."""

    applications = {seed.application for seed in seeds}
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if not isinstance(rule.head, GroundAssignmentHead):
                continue
            if rule.head.application in applications:
                continue
            if _rule_can_produce_value(rule, applications):
                applications.add(rule.head.application)
                changed = True
    return frozenset(applications)


class NativePropagator(clingo.Propagator):
    """Maintain seed state incrementally and constrain rule guards at total models."""

    def __init__(self, *, record_snapshots: bool = True) -> None:
        self._record_snapshots = record_snapshots
        self._seeds: tuple[GroundSeed, ...] = ()
        self._rules: tuple[GroundRule, ...] = ()
        self._native_literals: tuple[int, ...] = ()
        self._constant_seeds: tuple[GroundSeed, ...] = ()
        self._seeds_by_literal: dict[int, tuple[GroundSeed, ...]] = {}
        self._rules_by_application: dict[GroundApplication, tuple[int, ...]] = {}
        self._rule_activation_literals: frozenset[int] = frozenset()
        self._rule_order: tuple[int, ...] = ()
        self._potential_applications: frozenset[GroundApplication] = frozenset()
        self._early_evaluation_required = False
        self._ordinary_by_literal: dict[int, tuple[str, ...]] = {}
        self._constant_ordinary: tuple[str, ...] = ()
        self._states: dict[int, _ThreadState] = {}
        self._snapshots: dict[int, NativeSnapshot] = {}
        self._learned_clauses: dict[int, set[tuple[int, ...]]] = {}
        self._theory_atom_count = 0
        self._application_decode_requests = 0
        self._decoded_applications = 0
        self._application_cache_hits = 0
        self._value_decode_requests = 0
        self._decoded_values = 0
        self._value_cache_hits = 0
        self.init_seconds = 0.0
        self.check_count = 0
        self.undo_count = 0
        self.propagate_count = 0
        self.propagated_literal_count = 0
        self.seed_activation_count = 0
        self.seed_deactivation_count = 0
        self.ordinary_activation_count = 0
        self.ordinary_deactivation_count = 0
        self.check_seed_probe_count = 0
        self.rule_body_evaluation_count = 0
        self.blocking_clause_count = 0
        self.functionality_clause_count = 0
        self.derived_functionality_clause_count = 0
        self.guard_clause_count = 0
        self.narrow_blocking_clause_count = 0
        self.broad_blocking_clause_count = 0
        self._broad_clause_causes: dict[str, int] = {}
        self.duplicate_clause_count = 0
        self.clause_add_conflict_count = 0
        self.clause_propagation_count = 0
        self.early_explanation_clause_count = 0
        self.clause_literal_count = 0
        self.maximum_clause_width = 0
        self.snapshot_assignment_count = 0
        self.snapshot_build_seconds = 0.0
        self.undone_literal_count = 0

    def init(self, init: clingo.PropagateInit) -> None:
        started = time.perf_counter()
        if not 1 <= init.number_of_threads <= 2:
            raise RuntimeError("native feasibility prototype is evaluated for at most two threads")
        # Clingo can invoke a Total check with solver don't-cares still unassigned.
        # Explanations therefore use positive supports only; a fallback clause treats
        # every non-true native literal as a conditional completion, never as evidence
        # that the literal is already false.
        init.check_mode = clingo.PropagatorCheckMode.Total
        init.undo_mode = clingo.PropagatorUndoMode.Always
        seeds: list[GroundSeed] = []
        rules: dict[RuleKey, GroundRule] = {}
        guards: dict[RuleKey, int] = {}
        native_literals: set[int] = set()
        decoder = _TheoryDecoder()
        self._theory_atom_count = 0
        self._states.clear()
        self._snapshots.clear()
        self._learned_clauses.clear()
        self.check_count = 0
        self.undo_count = 0
        self.propagate_count = 0
        self.propagated_literal_count = 0
        self.seed_activation_count = 0
        self.seed_deactivation_count = 0
        self.ordinary_activation_count = 0
        self.ordinary_deactivation_count = 0
        self.check_seed_probe_count = 0
        self.rule_body_evaluation_count = 0
        self.blocking_clause_count = 0
        self.functionality_clause_count = 0
        self.derived_functionality_clause_count = 0
        self.guard_clause_count = 0
        self.narrow_blocking_clause_count = 0
        self.broad_blocking_clause_count = 0
        self._broad_clause_causes.clear()
        self.duplicate_clause_count = 0
        self.clause_add_conflict_count = 0
        self.clause_propagation_count = 0
        self.early_explanation_clause_count = 0
        self.clause_literal_count = 0
        self.maximum_clause_width = 0
        self.snapshot_assignment_count = 0
        self.snapshot_build_seconds = 0.0
        self.undone_literal_count = 0

        for atom in init.theory_atoms:
            self._theory_atom_count += 1
            name = atom.term.name
            literal = init.solver_literal(atom.literal)
            native_literals.add(literal)
            if name == "aspf_native_seed":
                seeds.append(_decode_seed(atom, literal, decoder))
            elif name == "aspf_native_rule":
                rule = _decode_rule(atom, literal, decoder)
                rules[rule.key] = rule
            elif name == "aspf_native_guard":
                key, guard_literal = _decode_guard(atom, literal)
                guards[key] = guard_literal

        self._application_decode_requests = decoder.application_requests
        self._decoded_applications = len(decoder.applications)
        self._application_cache_hits = decoder.application_cache_hits
        self._value_decode_requests = decoder.value_requests
        self._decoded_values = len(decoder.values)
        self._value_cache_hits = decoder.value_cache_hits

        self._seeds = tuple(sorted(seeds, key=lambda seed: (seed.application, seed.value)))
        self._rules = tuple(
            replace(rule, guard_literal=guards.get(key)) for key, rule in sorted(rules.items())
        )
        grouped_rules: dict[GroundApplication, list[int]] = {}
        for index, rule in enumerate(self._rules):
            for application in _rule_applications(rule):
                grouped_rules.setdefault(application, []).append(index)
        self._rules_by_application = {
            application: tuple(indexes) for application, indexes in grouped_rules.items()
        }
        self._rule_order = _rule_dependency_order(self._rules)
        self._rule_activation_literals = frozenset(
            rule.active_literal for rule in self._rules if abs(rule.active_literal) > 1
        )
        self._potential_applications = _potential_applications(self._seeds, self._rules)
        provider_counts: dict[GroundApplication, int] = {}
        for rule in self._rules:
            if isinstance(rule.head, GroundAssignmentHead):
                provider_counts[rule.head.application] = (
                    provider_counts.get(rule.head.application, 0) + 1
                )
        self._early_evaluation_required = bool(guards) or any(
            count > 1 for count in provider_counts.values()
        )
        self._native_literals = tuple(sorted(native_literals))
        ordinary_by_literal: dict[int, list[str]] = {}
        constant_ordinary: list[str] = []
        if self._record_snapshots:
            for symbolic_atom in init.symbolic_atoms:
                symbol = symbolic_atom.symbol
                if symbol.type is clingo.SymbolType.Function and symbol.name.startswith("__aspf_"):
                    continue
                literal = init.solver_literal(symbolic_atom.literal)
                rendered = str(symbol)
                if literal == 1:
                    constant_ordinary.append(rendered)
                elif literal != -1:
                    ordinary_by_literal.setdefault(literal, []).append(rendered)
        self._ordinary_by_literal = {
            literal: tuple(sorted(rendered)) for literal, rendered in ordinary_by_literal.items()
        }
        self._constant_ordinary = tuple(sorted(constant_ordinary))
        self._constant_seeds = tuple(seed for seed in self._seeds if seed.literal == 1)
        grouped_seeds: dict[int, list[GroundSeed]] = {}
        for seed in self._seeds:
            if abs(seed.literal) > 1:
                grouped_seeds.setdefault(seed.literal, []).append(seed)
        self._seeds_by_literal = {
            literal: tuple(grouped) for literal, grouped in grouped_seeds.items()
        }
        watched_literals = {literal for literal in self._native_literals if abs(literal) > 1}
        watched_literals.update(self._ordinary_by_literal)
        for literal in sorted(watched_literals):
            if abs(literal) > 1:
                init.add_watch(literal)
        self.init_seconds = time.perf_counter() - started

    @staticmethod
    def _add_seed(
        supports: dict[GroundApplication, dict[GroundValue, dict[int, int]]],
        seed: GroundSeed,
    ) -> None:
        values = supports.setdefault(seed.application, {})
        literals = values.setdefault(seed.value, {})
        literals[seed.literal] = literals.get(seed.literal, 0) + 1

    @staticmethod
    def _remove_seed(
        supports: dict[GroundApplication, dict[GroundValue, dict[int, int]]],
        seed: GroundSeed,
    ) -> None:
        values = supports[seed.application]
        literals = values[seed.value]
        remaining = literals[seed.literal] - 1
        if remaining:
            literals[seed.literal] = remaining
        else:
            del literals[seed.literal]
        if not literals:
            del values[seed.value]
        if not values:
            del supports[seed.application]

    def _state(self, thread_id: int) -> _ThreadState:
        state = self._states.get(thread_id)
        if state is not None:
            return state
        state = _ThreadState(set(), {}, {})
        for seed in self._constant_seeds:
            self._add_seed(state.seed_supports, seed)
        for atom in self._constant_ordinary:
            state.ordinary_supports[atom] = state.ordinary_supports.get(atom, 0) + 1
        self._states[thread_id] = state
        return state

    @staticmethod
    def _true(state: _ThreadState, literal: int) -> bool:
        if literal == 1:
            return True
        if literal == -1:
            return False
        return literal in state.true_literals

    def _block_current_native_assignment(
        self,
        control: clingo.PropagateControl,
        state: _ThreadState,
        *,
        functionality: bool = False,
        guard: bool = False,
        cause: str,
    ) -> None:
        """Exclude the current completion when no smaller justified reason is known."""

        clause = {
            -literal if self._true(state, literal) else literal
            for literal in self._native_literals
            if abs(literal) > 1
        }
        rendered = sorted(clause)
        key = tuple(rendered)
        learned = self._learned_clauses.setdefault(control.thread_id, set())
        if key in learned:
            self.duplicate_clause_count += 1
            return
        learned.add(key)
        self._record_clause(
            len(rendered),
            broad=True,
            functionality=functionality,
            guard=guard,
            derived_functionality=functionality,
        )
        self._broad_clause_causes[cause] = self._broad_clause_causes.get(cause, 0) + 1
        if control.add_clause(rendered):
            self.clause_propagation_count += 1
            control.propagate()
        else:
            self.clause_add_conflict_count += 1

    def _record_clause(
        self,
        width: int,
        *,
        broad: bool = False,
        functionality: bool = False,
        guard: bool = False,
        derived_functionality: bool = False,
    ) -> None:
        self.blocking_clause_count += 1
        self.clause_literal_count += width
        self.maximum_clause_width = max(self.maximum_clause_width, width)
        if broad:
            self.broad_blocking_clause_count += 1
        else:
            self.narrow_blocking_clause_count += 1
        if functionality:
            self.functionality_clause_count += 1
        if derived_functionality:
            self.derived_functionality_clause_count += 1
        if guard:
            self.guard_clause_count += 1

    @staticmethod
    def _seed_applications(state: _ThreadState) -> ApplicationValues:
        applications: ApplicationValues = {}
        for application, values in state.seed_supports.items():
            applications[application] = {
                value: frozenset() if 1 in literals else frozenset((min(literals),))
                for value, literals in values.items()
            }
        return applications

    def _seed_conflict_literals(self, state: _ThreadState) -> tuple[int, int] | None:
        for _application, supports in sorted(state.seed_supports.items()):
            values = sorted(supports)
            if len(values) < 2:
                continue
            literals = [min(supports[value]) for value in values[:2]]
            return literals[0], literals[1]
        return None

    def _block_seed_conflict(
        self,
        control: clingo.PropagateControl,
        literals: tuple[int, int],
    ) -> None:
        clause = sorted({-literal for literal in literals if literal != 1})
        self._record_clause(len(clause), functionality=True)
        if control.add_clause(clause, lock=True):
            self.clause_propagation_count += 1
            control.propagate()
        else:
            self.clause_add_conflict_count += 1

    def _block_explained_conflict(
        self,
        control: clingo.PropagateControl,
        explanation: Explanation,
        *,
        functionality: bool = False,
        guard: bool = False,
        required_literal: int | None = None,
        early: bool = False,
    ) -> bool | None:
        clause = {-literal for literal in explanation if abs(literal) > 1}
        if required_literal is not None and abs(required_literal) > 1:
            clause.add(required_literal)
        rendered = sorted(clause)
        key = tuple(rendered)
        learned = self._learned_clauses.setdefault(control.thread_id, set())
        if key in learned:
            self.duplicate_clause_count += 1
            return None
        learned.add(key)
        if early:
            self.early_explanation_clause_count += 1
        self._record_clause(
            len(rendered),
            functionality=functionality,
            guard=guard,
            derived_functionality=functionality,
        )
        if control.add_clause(rendered, lock=True):
            self.clause_propagation_count += 1
            return control.propagate()
        self.clause_add_conflict_count += 1
        return False

    @staticmethod
    def _application_conflict(
        applications: ApplicationValues,
    ) -> tuple[Explanation | None, Explanation | None] | None:
        for values in (applications[key] for key in sorted(applications)):
            if len(values) < 2:
                continue
            first, second = sorted(values)[:2]
            return values[first], values[second]
        return None

    def _evaluate_state(self, state: _ThreadState) -> _EvaluationState:
        applications = self._seed_applications(state)
        active = tuple(self._true(state, rule.active_literal) for rule in self._rules)
        pending = deque(index for index in self._rule_order if active[index])
        scheduled = set(pending)
        rule_states: dict[int, dict[str, ValueState]] = {}
        rule_satisfaction: dict[int, bool] = {}
        rule_explanations: dict[int, Explanation | None] = {}
        rule_explanation_gaps: dict[int, str | None] = {}
        while pending:
            index = pending.popleft()
            scheduled.remove(index)
            rule = self._rules[index]
            self.rule_body_evaluation_count += 1
            evaluation = _rule_body(rule, applications, self._potential_applications)
            active_explanation = (
                frozenset() if rule.active_literal == 1 else frozenset((rule.active_literal,))
            )
            explanation = _merge_explanations((active_explanation, evaluation.explanation))
            rule_states[index] = evaluation.nvariables
            rule_satisfaction[index] = evaluation.satisfied
            rule_explanations[index] = explanation
            rule_explanation_gaps[index] = evaluation.explanation_gap
            if not evaluation.satisfied or not isinstance(rule.head, GroundAssignmentHead):
                continue
            value = _evaluate_expression(
                rule.head.expression,
                applications,
                evaluation.nvariables,
                self._potential_applications,
            )
            if value.kind is not StateKind.DEFINED or value.value is None:
                continue
            value_explanation = _merge_explanations((explanation, value.explanation))
            candidates = applications.setdefault(rule.head.application, {})
            existing = candidates.get(value.value)
            if value.value in candidates and not _prefer_explanation(value_explanation, existing):
                continue
            new_value = value.value not in candidates
            candidates[value.value] = value_explanation
            if not new_value and existing == value_explanation:
                continue
            for dependent in self._rules_by_application.get(rule.head.application, ()):
                if active[dependent] and dependent not in scheduled:
                    pending.append(dependent)
                    scheduled.add(dependent)
        return _EvaluationState(
            applications,
            active,
            rule_states,
            rule_satisfaction,
            rule_explanations,
            rule_explanation_gaps,
        )

    def propagate(self, control: clingo.PropagateControl, changes: Sequence[int]) -> None:
        """Index newly true native literals without scanning unrelated seeds."""

        self.propagate_count += 1
        self.propagated_literal_count += len(changes)
        state = self._state(control.thread_id)
        semantic_change = False
        for literal in changes:
            state.true_literals.add(literal)
            for seed in self._seeds_by_literal.get(literal, ()):
                self._add_seed(state.seed_supports, seed)
                self.seed_activation_count += 1
                semantic_change = True
            if literal in self._rule_activation_literals:
                semantic_change = True
            for atom in self._ordinary_by_literal.get(literal, ()):
                state.ordinary_supports[atom] = state.ordinary_supports.get(atom, 0) + 1
                self.ordinary_activation_count += 1
        conflict = self._seed_conflict_literals(state)
        if conflict is not None:
            self._block_seed_conflict(control, conflict)
            return
        if not semantic_change or not self._early_evaluation_required:
            return
        evaluation = self._evaluate_state(state)
        application_conflict = self._application_conflict(evaluation.applications)
        if application_conflict is not None:
            explanation = _merge_explanations(application_conflict)
            if explanation is not None:
                self._block_explained_conflict(
                    control,
                    explanation,
                    functionality=True,
                    early=True,
                )
            return
        for index, rule in enumerate(self._rules):
            if rule.guard_literal is None:
                continue
            explanation = evaluation.rule_explanations.get(index)
            if explanation is None:
                continue
            expected = evaluation.rule_satisfaction.get(index, False)
            required_literal = rule.guard_literal if expected else -rule.guard_literal
            added = self._block_explained_conflict(
                control,
                explanation,
                guard=True,
                required_literal=required_literal,
                early=True,
            )
            if added is not None:
                return

    def check(self, control: clingo.PropagateControl) -> None:
        self.check_count += 1
        self._snapshots.pop(control.thread_id, None)
        state = self._state(control.thread_id)
        conflict = self._seed_conflict_literals(state)
        if conflict is not None:
            self._block_seed_conflict(control, conflict)
            return
        evaluation = self._evaluate_state(state)
        application_conflict = self._application_conflict(evaluation.applications)
        if application_conflict is not None:
            explanation = _merge_explanations(application_conflict)
            if explanation is None:
                self._block_current_native_assignment(
                    control,
                    state,
                    functionality=True,
                    cause="derived-functionality",
                )
            else:
                self._block_explained_conflict(
                    control,
                    explanation,
                    functionality=True,
                )
            return

        undefined = {
            (self._rules[index].key, name)
            for index, nvariables in evaluation.rule_states.items()
            for name, value_state in nvariables.items()
            if value_state.kind is StateKind.UNDEFINED
        }
        for index, rule in enumerate(self._rules):
            if rule.guard_literal is None:
                continue
            expected = evaluation.rule_satisfaction.get(index, False)
            actual = self._true(state, rule.guard_literal)
            if expected != actual:
                explanation = evaluation.rule_explanations.get(index)
                if explanation is None:
                    instance = ",".join(value.render() for value in rule.key.instance)
                    suffix = f"[{instance}]" if instance else ""
                    explanation_gap = evaluation.rule_explanation_gaps.get(index)
                    gap = f":{explanation_gap}" if explanation_gap else ""
                    self._block_current_native_assignment(
                        control,
                        state,
                        guard=True,
                        cause=f"guard:{rule.key.identifier}{suffix}{gap}",
                    )
                else:
                    required_literal = rule.guard_literal if expected else -rule.guard_literal
                    self._block_explained_conflict(
                        control,
                        explanation,
                        guard=True,
                        required_literal=required_literal,
                    )
                return

        if not self._record_snapshots:
            return
        snapshot_started = time.perf_counter()
        assignments = tuple(
            sorted(
                (application, next(iter(values)))
                for application, values in evaluation.applications.items()
                if len(values) == 1
            )
        )
        self._snapshots[control.thread_id] = NativeSnapshot(
            ordinary_atoms=tuple(sorted(state.ordinary_supports)),
            assignments=assignments,
            undefined_nvariables=tuple(sorted(undefined)),
        )
        self.snapshot_assignment_count += len(assignments)
        self.snapshot_build_seconds += time.perf_counter() - snapshot_started

    def undo(
        self,
        thread_id: int,
        assignment: clingo.Assignment,
        changes: Sequence[int],
    ) -> None:
        del assignment
        self.undo_count += 1
        self.undone_literal_count += len(changes)
        state = self._state(thread_id)
        for literal in changes:
            state.true_literals.remove(literal)
            for seed in self._seeds_by_literal.get(literal, ()):
                self._remove_seed(state.seed_supports, seed)
                self.seed_deactivation_count += 1
            for atom in self._ordinary_by_literal.get(literal, ()):
                remaining = state.ordinary_supports[atom] - 1
                if remaining:
                    state.ordinary_supports[atom] = remaining
                else:
                    del state.ordinary_supports[atom]
                self.ordinary_deactivation_count += 1
        self._snapshots.pop(thread_id, None)

    def snapshot(self, thread_id: int) -> NativeSnapshot:
        """Return the valid state computed for the current model callback."""

        try:
            return self._snapshots[thread_id]
        except KeyError as error:
            raise RuntimeError("native snapshot is unavailable for this model") from error

    def metrics(self) -> NativeWorkMetrics:
        """Return deterministic work counters for tests and benchmark evidence."""

        return NativeWorkMetrics(
            theory_atoms=self._theory_atom_count,
            seeds=len(self._seeds),
            rules=len(self._rules),
            application_decode_requests=self._application_decode_requests,
            decoded_applications=self._decoded_applications,
            application_cache_hits=self._application_cache_hits,
            value_decode_requests=self._value_decode_requests,
            decoded_values=self._decoded_values,
            value_cache_hits=self._value_cache_hits,
            watched_literals=sum(abs(literal) > 1 for literal in self._native_literals),
            ordinary_atoms=len(self._constant_ordinary)
            + sum(len(atoms) for atoms in self._ordinary_by_literal.values()),
            ordinary_watched_literals=len(self._ordinary_by_literal),
            ordinary_activations=self.ordinary_activation_count,
            ordinary_deactivations=self.ordinary_deactivation_count,
            propagate_calls=self.propagate_count,
            propagated_literals=self.propagated_literal_count,
            seed_activations=self.seed_activation_count,
            seed_deactivations=self.seed_deactivation_count,
            check_calls=self.check_count,
            check_seed_probes=self.check_seed_probe_count,
            rule_body_evaluations=self.rule_body_evaluation_count,
            blocking_clauses=self.blocking_clause_count,
            functionality_clauses=self.functionality_clause_count,
            derived_functionality_clauses=self.derived_functionality_clause_count,
            guard_clauses=self.guard_clause_count,
            narrow_blocking_clauses=self.narrow_blocking_clause_count,
            broad_blocking_clauses=self.broad_blocking_clause_count,
            broad_clause_causes=tuple(sorted(self._broad_clause_causes.items())),
            duplicate_clauses=self.duplicate_clause_count,
            clause_add_conflicts=self.clause_add_conflict_count,
            clause_propagations=self.clause_propagation_count,
            early_explanation_clauses=self.early_explanation_clause_count,
            clause_literals=self.clause_literal_count,
            maximum_clause_width=self.maximum_clause_width,
            snapshot_assignments=self.snapshot_assignment_count,
            undo_calls=self.undo_count,
            undone_literals=self.undone_literal_count,
        )
