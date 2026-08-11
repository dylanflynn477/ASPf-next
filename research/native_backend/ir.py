"""Typed IR for the native-backend feasibility experiment."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

from research.native_backend.errors import NativeValidationError

_IDENTIFIER = re.compile(r"^[a-z][A-Za-z0-9_]*$")
_VARIABLE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
_NVARIABLE = re.compile(r"^[a-z][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Source coordinate retained by the research IR."""

    filename: str = "<research>"
    line: int = 1
    column: int = 1


def _diagnostic(message: str, location: SourceLocation) -> NativeValidationError:
    return NativeValidationError(message, location.filename, location.line, location.column)


@dataclass(frozen=True, slots=True)
class Integer:
    """Integer term."""

    value: int

    def render(self) -> str:
        return str(self.value)

    def encode_value(self) -> str:
        return f"integer({self.value})"


@dataclass(frozen=True, slots=True)
class Symbol:
    """Lowercase symbolic constant."""

    name: str

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.name):
            raise ValueError(f"invalid symbolic constant: {self.name!r}")

    def render(self) -> str:
        return self.name

    def encode_value(self) -> str:
        return f"symbol({self.name})"


@dataclass(frozen=True, slots=True)
class String:
    """Quoted string value."""

    value: str

    def render(self) -> str:
        return json.dumps(self.value, ensure_ascii=False)

    def encode_value(self) -> str:
        return f"string({self.render()})"


@dataclass(frozen=True, slots=True)
class Variable:
    """Ordinary Clingo variable, grounded before propagation."""

    name: str

    def __post_init__(self) -> None:
        if not _VARIABLE.fullmatch(self.name):
            raise ValueError(f"invalid ordinary variable: {self.name!r}")

    def render(self) -> str:
        return self.name

    def encode_value(self) -> str:
        return f"ordinary({self.name})"


Term: TypeAlias = Integer | Symbol | String | Variable
GroundTerm: TypeAlias = Integer | Symbol | String


@dataclass(frozen=True, slots=True)
class Atom:
    """Ordinary ASP atom used by the typed source generator."""

    name: str
    arguments: tuple[Term, ...] = ()
    location: SourceLocation = field(default_factory=SourceLocation)

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.name) or self.name.startswith("__aspf_"):
            raise ValueError(f"invalid or reserved atom name: {self.name!r}")
        if any(
            not isinstance(term, (Integer, Symbol, String, Variable)) for term in self.arguments
        ):
            raise _diagnostic(
                "non-Herbrand variables cannot occur in ordinary atom arguments",
                self.location,
            )

    def render(self) -> str:
        if not self.arguments:
            return self.name
        return f"{self.name}({','.join(argument.render() for argument in self.arguments)})"


@dataclass(frozen=True, slots=True)
class Choice:
    """Exactly-one ordinary choice over a typed atom and integer interval."""

    atom_name: str
    variable: Variable
    lower: int
    upper: int

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.atom_name) or self.atom_name.startswith("__aspf_"):
            raise ValueError(f"invalid or reserved choice atom: {self.atom_name!r}")
        if self.lower > self.upper:
            raise ValueError("choice lower bound exceeds upper bound")

    def render(self) -> str:
        interval = f"{self.variable.name}={self.lower}..{self.upper}"
        return f"1 {{ {self.atom_name}({self.variable.name}) : {interval} }} 1."


@dataclass(frozen=True, slots=True)
class Application:
    """A non-Herbrand application key."""

    function: str
    arguments: tuple[Term, ...] = ()
    location: SourceLocation = field(default_factory=SourceLocation)

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.function) or self.function.startswith("__aspf_"):
            raise ValueError(f"invalid or reserved function name: {self.function!r}")
        if any(
            not isinstance(term, (Integer, Symbol, String, Variable)) for term in self.arguments
        ):
            raise _diagnostic(
                "non-Herbrand variables cannot occur in application arguments",
                self.location,
            )

    def encode(self) -> str:
        suffix = "".join(f",{argument.render()}" for argument in self.arguments)
        return f"app({self.function}{suffix})"


@dataclass(frozen=True, slots=True)
class NVariable:
    """Rule-local non-Herbrand variable identity."""

    name: str

    def __post_init__(self) -> None:
        normalized = self.name.removeprefix("_")
        if not _NVARIABLE.fullmatch(normalized):
            raise ValueError(f"invalid non-Herbrand variable: {self.name!r}")
        object.__setattr__(self, "name", normalized)

    def encode(self) -> str:
        return f"nvar({self.name})"


@dataclass(frozen=True, slots=True)
class ConstantExpression:
    """A constant value expression."""

    value: Term

    def encode(self) -> str:
        return f"constant({self.value.encode_value()})"


@dataclass(frozen=True, slots=True)
class AppExpression:
    """The value of a non-Herbrand application."""

    application: Application

    def encode(self) -> str:
        return f"application({self.application.encode()})"


@dataclass(frozen=True, slots=True)
class NVariableExpression:
    """The value of a rule-local non-Herbrand variable."""

    variable: NVariable

    def encode(self) -> str:
        return f"nvalue({self.variable.encode()})"


Expression: TypeAlias = ConstantExpression | AppExpression | NVariableExpression


@dataclass(frozen=True, slots=True)
class Definition:
    """A positive defining equality for an n-variable."""

    variable: NVariable
    expression: Expression

    def encode(self) -> str:
        return f"define({self.variable.encode()},{self.expression.encode()})"


class ComparisonOperator(Enum):
    """Comparison operators evaluated by the experimental propagator."""

    EQUAL = "eq"
    NOT_EQUAL = "ne"
    LESS = "lt"
    LESS_EQUAL = "le"
    GREATER = "gt"
    GREATER_EQUAL = "ge"


@dataclass(frozen=True, slots=True)
class Comparison:
    """A positive or default-negated solver-time comparison."""

    left: Expression
    operator: ComparisonOperator
    right: Expression
    default_negated: bool = False

    def encode(self) -> str:
        polarity = "default_negated" if self.default_negated else "positive"
        return (
            f"compare({self.operator.value},{polarity},{self.left.encode()},{self.right.encode()})"
        )


@dataclass(frozen=True, slots=True)
class AssignmentHead:
    """A solver-time non-Herbrand assignment head."""

    application: Application
    value: Expression

    def encode(self) -> str:
        return f"head_assignment({self.application.encode()},{self.value.encode()})"


@dataclass(frozen=True, slots=True)
class AtomHead:
    """An ordinary visible atom controlled by solver-time comparisons."""

    atom: Atom

    def encode(self) -> str:
        suffix = "".join(f",{argument.render()}" for argument in self.atom.arguments)
        return f"head_atom(atom({self.atom.name}{suffix}))"


RuleHead: TypeAlias = AssignmentHead | AtomHead


@dataclass(frozen=True, slots=True)
class Seed:
    """A groundable source assignment activated by ordinary ASP conditions."""

    application: Application
    value: Term
    when: tuple[Atom, ...] = ()
    location: SourceLocation = field(default_factory=SourceLocation)


@dataclass(frozen=True, slots=True)
class NativeRule:
    """A typed rule evaluated partly by Clingo and partly by the propagator."""

    identifier: str
    head: RuleHead
    definitions: tuple[Definition, ...] = ()
    comparisons: tuple[Comparison, ...] = ()
    when: tuple[Atom, ...] = ()
    location: SourceLocation = field(default_factory=SourceLocation)

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.identifier):
            raise ValueError(f"invalid rule identifier: {self.identifier!r}")


@dataclass(frozen=True, slots=True)
class NativeProgram:
    """Complete input to the isolated native solver."""

    facts: tuple[Atom, ...] = ()
    choices: tuple[Choice, ...] = ()
    seeds: tuple[Seed, ...] = ()
    rules: tuple[NativeRule, ...] = ()


def variables_in_term(term: Term) -> set[str]:
    """Return ordinary variables in a typed term."""

    return {term.name} if isinstance(term, Variable) else set()


def variables_in_application(application: Application) -> set[str]:
    """Return ordinary variables in an application key."""

    return set().union(*(variables_in_term(term) for term in application.arguments))


def variables_in_atom(atom: Atom) -> set[str]:
    """Return ordinary variables in an ordinary atom."""

    return set().union(*(variables_in_term(term) for term in atom.arguments))


def variables_in_expression(expression: Expression) -> set[str]:
    """Return ordinary variables in an expression."""

    if isinstance(expression, ConstantExpression):
        return variables_in_term(expression.value)
    if isinstance(expression, AppExpression):
        return variables_in_application(expression.application)
    return set()


def nvariables_in_expression(expression: Expression) -> set[str]:
    """Return rule-local n-variable names referenced by an expression."""

    if isinstance(expression, NVariableExpression):
        return {expression.variable.name}
    return set()


def applications_in_expression(expression: Expression) -> set[Application]:
    """Return application dependencies referenced by an expression."""

    if isinstance(expression, AppExpression):
        return {expression.application}
    return set()


def raise_at(message: str, location: SourceLocation) -> None:
    """Raise a location-aware experimental diagnostic."""

    raise _diagnostic(message, location)
