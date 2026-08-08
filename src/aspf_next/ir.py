"""Typed intermediate representation for the first compatibility slice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from aspf_next.source import SourceSpan


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
class VariableTerm:
    """A source-level ordinary variable used as a direct application argument."""

    name: str
    span: SourceSpan

    @property
    def text(self) -> str:
        """Return the source spelling used by the reference lowering."""

        return self.name


ApplicationArgument = GroundTerm | VariableTerm


@dataclass(frozen=True, slots=True)
class FunctionApplication:
    """A declared non-Herbrand function application."""

    name: str
    arguments: tuple[ApplicationArgument, ...]

    def render(self) -> str:
        if not self.arguments:
            return self.name
        arguments = ",".join(argument.text for argument in self.arguments)
        return f"{self.name}({arguments})"


@dataclass(frozen=True, slots=True)
class ScalarOperand:
    """A restricted ground scalar operand with its source span."""

    term: GroundTerm
    span: SourceSpan

    @property
    def text(self) -> str:
        """Return the validated source spelling."""

        return self.term.text

    @property
    def kind(self) -> GroundTermKind:
        """Return the scalar's validated lexical kind."""

        return self.term.kind


@dataclass(frozen=True, slots=True)
class ValueVariableOperand:
    """An ordinary source variable occupying a body n-atom value position."""

    name: str
    span: SourceSpan

    @property
    def text(self) -> str:
        """Return the source spelling used by the reference lowering."""

        return self.name


@dataclass(frozen=True, slots=True)
class ApplicationOperand:
    """A non-Herbrand application operand and its source span."""

    application: FunctionApplication
    span: SourceSpan

    def render(self) -> str:
        """Render the application in the reference backend's key syntax."""

        return self.application.render()


ComparisonOperand: TypeAlias = ScalarOperand | ValueVariableOperand | ApplicationOperand


@dataclass(frozen=True, slots=True)
class Assignment:
    """A seed assignment from an application target to a ground scalar."""

    target: ApplicationOperand
    value: ScalarOperand
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class BodyComparison:
    """A dependent comparison in a rule body, with explicit polarity."""

    left: ApplicationOperand
    right: ComparisonOperand
    operator: NAtomOperator
    span: SourceSpan
    negated: bool = False


NAtom: TypeAlias = Assignment | BodyComparison


@dataclass(frozen=True, slots=True)
class NHerbDeclaration:
    """A local non-Herbrand function declaration."""

    name: str
    arity: int
    span: SourceSpan


class VisibilityAction(Enum):
    """Presentation action for reconstructed non-Herbrand assignments."""

    SHOW = "show"
    HIDE = "hide"


@dataclass(frozen=True, slots=True)
class NHerbVisibilityDirective:
    """An ordered all-assignments or exact name/arity visibility directive."""

    action: VisibilityAction
    name: str | None
    arity: int | None
    span: SourceSpan

    def selects(self, name: str, arity: int) -> bool:
        """Return whether this directive applies to the given application key."""

        return self.name is None or (self.name == name and self.arity == arity)


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
    global_nherb: bool = False
    nherb_visibility: tuple[NHerbVisibilityDirective, ...] = ()
