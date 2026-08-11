"""Thread-scoped solver state for the native-backend feasibility prototype."""

from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Sequence
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


UNDEFINED = ValueState(StateKind.UNDEFINED)


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
    snapshot_assignments: int
    undo_calls: int
    undone_literals: int


@dataclass(slots=True)
class _ThreadState:
    """Assignment-dependent state owned by one Clingo solving thread."""

    true_literals: set[int]
    seed_supports: dict[GroundApplication, dict[GroundValue, int]]
    ordinary_supports: dict[str, int]


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
    definitions = tuple(
        _decode_definition(term, decoder) for term in terms[2:] if term.name == "define"
    )
    comparisons = tuple(
        _decode_comparison(term, decoder) for term in terms[2:] if term.name == "compare"
    )
    return GroundRule(
        key=_decode_meta(terms[0]),
        head=_decode_head(terms[1], decoder),
        definitions=definitions,
        comparisons=comparisons,
        active_literal=literal,
    )


def _decode_guard(atom: clingo.TheoryAtom, literal: int) -> tuple[RuleKey, int]:
    terms = _element_terms(atom)
    if len(terms) != 1:
        raise RuntimeError(f"invalid native guard: {atom}")
    return _decode_meta(terms[0]), literal


def _application_state(
    values: dict[GroundApplication, set[GroundValue]], application: GroundApplication
) -> ValueState:
    candidates = values.get(application, set())
    if not candidates:
        return UNDEFINED
    if len(candidates) > 1:
        return ValueState(StateKind.CONFLICT)
    return ValueState(StateKind.DEFINED, next(iter(candidates)))


def _evaluate_expression(
    expression: GroundExpression,
    applications: dict[GroundApplication, set[GroundValue]],
    nvariables: dict[str, ValueState],
) -> ValueState:
    if isinstance(expression, ConstantGroundExpression):
        return ValueState(StateKind.DEFINED, expression.value)
    if isinstance(expression, ApplicationGroundExpression):
        return _application_state(applications, expression.application)
    return nvariables.get(expression.name, UNDEFINED)


def _resolve_nvariables(
    rule: GroundRule,
    applications: dict[GroundApplication, set[GroundValue]],
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
                _evaluate_expression(expression, applications, resolved)
                for expression in expressions
            ]
            values = {
                state.value
                for state in states
                if state.kind is StateKind.DEFINED and state.value is not None
            }
            if all(state.kind is StateKind.DEFINED for state in states) and len(values) == 1:
                resolved[name] = ValueState(StateKind.DEFINED, next(iter(values)))
            else:
                resolved[name] = UNDEFINED
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
    applications: dict[GroundApplication, set[GroundValue]],
) -> tuple[bool, dict[str, ValueState]]:
    nvariables = _resolve_nvariables(rule, applications)
    definitions_satisfied = all(
        nvariables[definition.variable].kind is StateKind.DEFINED
        and _evaluate_expression(definition.expression, applications, nvariables)
        == nvariables[definition.variable]
        for definition in rule.definitions
    )
    if not definitions_satisfied:
        return False, nvariables
    for comparison in rule.comparisons:
        left = _evaluate_expression(comparison.left, applications, nvariables)
        right = _evaluate_expression(comparison.right, applications, nvariables)
        positive = (
            left.kind is StateKind.DEFINED
            and right.kind is StateKind.DEFINED
            and left.value is not None
            and right.value is not None
            and _compare_values(left.value, comparison.operator, right.value)
        )
        satisfied = not positive if comparison.default_negated else positive
        if not satisfied:
            return False, nvariables
    return True, nvariables


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
        self._rule_order: tuple[int, ...] = ()
        self._ordinary_by_literal: dict[int, tuple[str, ...]] = {}
        self._constant_ordinary: tuple[str, ...] = ()
        self._states: dict[int, _ThreadState] = {}
        self._snapshots: dict[int, NativeSnapshot] = {}
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
        self.snapshot_assignment_count = 0
        self.snapshot_build_seconds = 0.0
        self.undone_literal_count = 0

    def init(self, init: clingo.PropagateInit) -> None:
        started = time.perf_counter()
        if init.number_of_threads != 1:
            raise RuntimeError("native feasibility prototype requires exactly one solver thread")
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
        supports: dict[GroundApplication, dict[GroundValue, int]],
        seed: GroundSeed,
    ) -> None:
        values = supports.setdefault(seed.application, {})
        values[seed.value] = values.get(seed.value, 0) + 1

    @staticmethod
    def _remove_seed(
        supports: dict[GroundApplication, dict[GroundValue, int]],
        seed: GroundSeed,
    ) -> None:
        values = supports[seed.application]
        remaining = values[seed.value] - 1
        if remaining:
            values[seed.value] = remaining
        else:
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
    ) -> None:
        clause = {
            -literal if self._true(state, literal) else literal
            for literal in self._native_literals
            if abs(literal) > 1
        }
        self.blocking_clause_count += 1
        control.add_clause(sorted(clause))

    def propagate(self, control: clingo.PropagateControl, changes: Sequence[int]) -> None:
        """Index newly true native literals without scanning unrelated seeds."""

        self.propagate_count += 1
        self.propagated_literal_count += len(changes)
        state = self._state(control.thread_id)
        for literal in changes:
            state.true_literals.add(literal)
            for seed in self._seeds_by_literal.get(literal, ()):
                self._add_seed(state.seed_supports, seed)
                self.seed_activation_count += 1
            for atom in self._ordinary_by_literal.get(literal, ()):
                state.ordinary_supports[atom] = state.ordinary_supports.get(atom, 0) + 1
                self.ordinary_activation_count += 1

    def check(self, control: clingo.PropagateControl) -> None:
        self.check_count += 1
        self._snapshots.pop(control.thread_id, None)
        state = self._state(control.thread_id)
        applications = {
            application: set(values) for application, values in state.seed_supports.items()
        }
        if any(len(values) > 1 for values in applications.values()):
            self._block_current_native_assignment(control, state)
            return

        active = tuple(self._true(state, rule.active_literal) for rule in self._rules)
        pending = deque(index for index in self._rule_order if active[index])
        scheduled = set(pending)
        rule_states: dict[int, dict[str, ValueState]] = {}
        rule_satisfaction: dict[int, bool] = {}
        while pending:
            index = pending.popleft()
            scheduled.remove(index)
            rule = self._rules[index]
            self.rule_body_evaluation_count += 1
            satisfied, nvariables = _rule_body(rule, applications)
            rule_states[index] = nvariables
            rule_satisfaction[index] = satisfied
            if not satisfied or not isinstance(rule.head, GroundAssignmentHead):
                continue
            value = _evaluate_expression(rule.head.expression, applications, nvariables)
            if value.kind is not StateKind.DEFINED or value.value is None:
                continue
            candidates = applications.setdefault(rule.head.application, set())
            old_size = len(candidates)
            candidates.add(value.value)
            if len(candidates) == old_size:
                continue
            for dependent in self._rules_by_application.get(rule.head.application, ()):
                if active[dependent] and dependent not in scheduled:
                    pending.append(dependent)
                    scheduled.add(dependent)
        if any(len(values) > 1 for values in applications.values()):
            self._block_current_native_assignment(control, state)
            return

        undefined = {
            (self._rules[index].key, name)
            for index, nvariables in rule_states.items()
            for name, value_state in nvariables.items()
            if value_state.kind is StateKind.UNDEFINED
        }
        for index, rule in enumerate(self._rules):
            if rule.guard_literal is None:
                continue
            expected = rule_satisfaction.get(index, False)
            actual = self._true(state, rule.guard_literal)
            if expected != actual:
                self._block_current_native_assignment(control, state)
                return

        if not self._record_snapshots:
            return
        snapshot_started = time.perf_counter()
        assignments = tuple(
            sorted(
                (application, next(iter(values)))
                for application, values in applications.items()
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
            snapshot_assignments=self.snapshot_assignment_count,
            undo_calls=self.undo_count,
            undone_literals=self.undone_literal_count,
        )
