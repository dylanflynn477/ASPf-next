"""Typed intermediate representation for the first compatibility slice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aspf_next.source import SourceSpan


class NAtomRole(Enum):
    """Where an n-atom occurs in a rule."""

    HEAD = "head"
    BODY = "body"


@dataclass(frozen=True, slots=True)
class GroundTerm:
    """A validated, ground Clingo term retained in source form."""

    text: str


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
    """A supported equality assignment or positive comparison."""

    application: FunctionApplication
    value: GroundTerm
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
