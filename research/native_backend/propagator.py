"""Thread-scoped solver state for the native-backend feasibility prototype."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import TypeAlias

import clingo


class ValueKind(Enum):
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


class StateKind(Enum):
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

    assignments: tuple[tuple[GroundApplication, GroundValue], ...]
    undefined_nvariables: tuple[tuple[RuleKey, str], ...]


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


def _decode_expression(term: clingo.TheoryTerm) -> GroundExpression:
    if term.type is not clingo.TheoryTermType.Function or len(term.arguments) != 1:
        raise RuntimeError(f"invalid native expression: {term}")
    if term.name == "constant":
        return ConstantGroundExpression(_decode_value(term.arguments[0]))
    if term.name == "application":
        return ApplicationGroundExpression(_decode_application(term.arguments[0]))
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


def _decode_head(term: clingo.TheoryTerm) -> GroundHead:
    if term.type is not clingo.TheoryTermType.Function:
        raise RuntimeError(f"invalid native rule head: {term}")
    if term.name == "head_assignment" and len(term.arguments) == 2:
        return GroundAssignmentHead(
            _decode_application(term.arguments[0]),
            _decode_expression(term.arguments[1]),
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


def _decode_definition(term: clingo.TheoryTerm) -> GroundDefinition:
    _expect_function(term, "define", 2)
    return GroundDefinition(
        _decode_nvariable(term.arguments[0]),
        _decode_expression(term.arguments[1]),
    )


def _decode_comparison(term: clingo.TheoryTerm) -> GroundComparison:
    _expect_function(term, "compare", 4)
    operator_term, polarity_term, left_term, right_term = term.arguments
    if (
        operator_term.type is not clingo.TheoryTermType.Symbol
        or polarity_term.type is not clingo.TheoryTermType.Symbol
    ):
        raise RuntimeError(f"invalid native comparison: {term}")
    return GroundComparison(
        _decode_expression(left_term),
        GroundComparisonOperator(operator_term.name),
        _decode_expression(right_term),
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


def _decode_seed(atom: clingo.TheoryAtom, literal: int) -> GroundSeed:
    terms = _element_terms(atom)
    if len(terms) != 1:
        raise RuntimeError(f"invalid native seed: {atom}")
    assignment = terms[0]
    _expect_function(assignment, "assignment", 2)
    return GroundSeed(
        _decode_application(assignment.arguments[0]),
        _decode_value(assignment.arguments[1]),
        literal,
    )


def _decode_rule(atom: clingo.TheoryAtom, literal: int) -> GroundRule:
    terms = _element_terms(atom)
    if len(terms) < 2:
        raise RuntimeError(f"native rule lacks metadata or head: {atom}")
    definitions = tuple(_decode_definition(term) for term in terms[2:] if term.name == "define")
    comparisons = tuple(_decode_comparison(term) for term in terms[2:] if term.name == "compare")
    return GroundRule(
        key=_decode_meta(terms[0]),
        head=_decode_head(terms[1]),
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


class NativePropagator(clingo.Propagator):
    """Recompute deterministic n-state at total assignments and constrain guards."""

    def __init__(self) -> None:
        self._seeds: tuple[GroundSeed, ...] = ()
        self._rules: tuple[GroundRule, ...] = ()
        self._native_literals: tuple[int, ...] = ()
        self._snapshots: dict[int, NativeSnapshot] = {}
        self.check_count = 0
        self.undo_count = 0

    def init(self, init: clingo.PropagateInit) -> None:
        if init.number_of_threads != 1:
            raise RuntimeError("native feasibility prototype requires exactly one solver thread")
        init.check_mode = clingo.PropagatorCheckMode.Total
        init.undo_mode = clingo.PropagatorUndoMode.Always
        seeds: list[GroundSeed] = []
        rules: dict[RuleKey, GroundRule] = {}
        guards: dict[RuleKey, int] = {}
        native_literals: set[int] = set()
        self._snapshots.clear()

        for atom in init.theory_atoms:
            name = atom.term.name
            literal = init.solver_literal(atom.literal)
            native_literals.add(literal)
            if name == "aspf_native_seed":
                seeds.append(_decode_seed(atom, literal))
            elif name == "aspf_native_rule":
                rule = _decode_rule(atom, literal)
                rules[rule.key] = rule
            elif name == "aspf_native_guard":
                key, guard_literal = _decode_guard(atom, literal)
                guards[key] = guard_literal

        self._seeds = tuple(sorted(seeds, key=lambda seed: (seed.application, seed.value)))
        self._rules = tuple(
            replace(rule, guard_literal=guards.get(key)) for key, rule in sorted(rules.items())
        )
        self._native_literals = tuple(sorted(native_literals))
        for literal in self._native_literals:
            if abs(literal) > 1:
                init.add_watch(literal)
                init.add_watch(-literal)

    def _true(self, assignment: clingo.Assignment, literal: int) -> bool:
        return assignment.value(literal) is True

    def _block_current_native_assignment(self, control: clingo.PropagateControl) -> None:
        clause: list[int] = []
        for literal in self._native_literals:
            value = control.assignment.value(literal)
            if value is True:
                clause.append(-literal)
            elif value is False:
                clause.append(literal)
        control.add_clause(clause)

    def check(self, control: clingo.PropagateControl) -> None:
        self.check_count += 1
        applications: dict[GroundApplication, set[GroundValue]] = {}
        for seed in self._seeds:
            if self._true(control.assignment, seed.literal):
                applications.setdefault(seed.application, set()).add(seed.value)
        if any(len(values) > 1 for values in applications.values()):
            self._block_current_native_assignment(control)
            return

        undefined: set[tuple[RuleKey, str]] = set()
        for _iteration in range(len(self._rules) + 1):
            changed = False
            for rule in self._rules:
                if not self._true(control.assignment, rule.active_literal):
                    continue
                satisfied, nvariables = _rule_body(rule, applications)
                undefined.update(
                    (rule.key, name)
                    for name, state in nvariables.items()
                    if state.kind is StateKind.UNDEFINED
                )
                if not satisfied or not isinstance(rule.head, GroundAssignmentHead):
                    continue
                value = _evaluate_expression(rule.head.expression, applications, nvariables)
                if value.kind is not StateKind.DEFINED or value.value is None:
                    continue
                candidates = applications.setdefault(rule.head.application, set())
                old_size = len(candidates)
                candidates.add(value.value)
                changed = changed or len(candidates) != old_size
            if not changed:
                break
        if any(len(values) > 1 for values in applications.values()):
            self._block_current_native_assignment(control)
            return

        for rule in self._rules:
            if rule.guard_literal is None:
                continue
            expected = False
            if self._true(control.assignment, rule.active_literal):
                expected, nvariables = _rule_body(rule, applications)
                undefined.update(
                    (rule.key, name)
                    for name, state in nvariables.items()
                    if state.kind is StateKind.UNDEFINED
                )
            actual = self._true(control.assignment, rule.guard_literal)
            if expected != actual:
                self._block_current_native_assignment(control)
                return

        assignments = tuple(
            sorted(
                (application, next(iter(values)))
                for application, values in applications.items()
                if len(values) == 1
            )
        )
        self._snapshots[control.thread_id] = NativeSnapshot(
            assignments=assignments,
            undefined_nvariables=tuple(sorted(undefined)),
        )

    def undo(
        self,
        thread_id: int,
        assignment: clingo.Assignment,
        changes: Sequence[int],
    ) -> None:
        del assignment, changes
        self.undo_count += 1
        self._snapshots.pop(thread_id, None)

    def snapshot(self, thread_id: int) -> NativeSnapshot:
        """Return the valid state computed for the current model callback."""

        try:
            return self._snapshots[thread_id]
        except KeyError as error:
            raise RuntimeError("native snapshot is unavailable for this model") from error
