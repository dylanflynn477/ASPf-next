"""Typed intermediate representation for the first compatibility slice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aspf_next.source import SourceSpan


class NAtomRole(Enum):
    """Where an n-atom occurs in a rule."""

    HEAD = "head"
    BODY = "body"


class NAtomOperator(Enum):
    """A supported non-Herbrand comparison operator."""

    EQUAL = "#="
    NOT_EQUAL = "#!="
    LESS_THAN = "#<"
    LESS_EQUAL = "#<="
    GREATER_THAN = "#>"
    GREATER_EQUAL = "#>="

    @property
    def is_ordered(self) -> bool:
        """Whether the operator requires integer operands."""

        return self in {
            NAtomOperator.LESS_THAN,
            NAtomOperator.LESS_EQUAL,
            NAtomOperator.GREATER_THAN,
            NAtomOperator.GREATER_EQUAL,
        }

    @property
    def clingo_symbol(self) -> str:
        """Return the corresponding ordinary Clingo comparison spelling."""

        return self.value[1:]


class GroundTermKind(Enum):
    """The validated lexical kind of a ground term."""

    INTEGER = "integer"
    SYMBOL = "symbol"
    STRING = "string"
    FUNCTION = "function"


@dataclass(frozen=True, slots=True)
class GroundTerm:
    """A validated, ground Clingo term retained in source form."""

    text: str
    kind: GroundTermKind


@dataclass(frozen=True, slots=True)
class FunctionApplication:
    """A declared, ground non-Herbrand function application."""

    name: str
    arguments: tuple[GroundTerm, ...]

    def render(self) -> str:
        if not self.arguments:
            return self.name
        arguments = ",".join(argument.text for argument in self.arguments)
        return f"{self.name}({arguments})"


@dataclass(frozen=True, slots=True)
class NAtom:
    """A supported assignment or positive comparison."""

    application: FunctionApplication
    value: GroundTerm
    operator: NAtomOperator
    role: NAtomRole
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class NHerbDeclaration:
    """A local non-Herbrand function declaration."""

    name: str
    arity: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class OrdinaryStatement:
    """A source statement requiring no compatibility lowering."""

    text: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class AspfStatement:
    """A statement containing one or more validated n-atoms."""

    text: str
    span: SourceSpan
    n_atoms: tuple[NAtom, ...]


ProgramStatement = OrdinaryStatement | AspfStatement


@dataclass(frozen=True, slots=True)
class Program:
    """Parsed compatibility program, before lowering."""

    declarations: tuple[NHerbDeclaration, ...]
    statements: tuple[ProgramStatement, ...]
    filename: str
