"""Compatibility parser for the deliberately restricted ASP{f} milestone."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Never

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.ir import (
    ApplicationArgument,
    ApplicationOperand,
    AspfStatement,
    Assignment,
    BodyComparison,
    ComparisonOperand,
    FunctionApplication,
    GroundTerm,
    GroundTermKind,
    NAtom,
    NAtomOperator,
    NHerbDeclaration,
    OrdinaryStatement,
    Program,
    ProgramStatement,
    ScalarOperand,
    VariableTerm,
)
from aspf_next.source import (
    ScannedStatement,
    ScanPoint,
    SourceSpan,
    SourceText,
    executable_mask,
    scan_points,
    split_statements,
)

_DECLARATION = re.compile(r"^\s*#nherb\s+([a-z][A-Za-z0-9_]*)\s*/\s*(\d+)\s*\.\s*$")
_APPLICATION_DECLARATION = re.compile(
    r"^\s*#nherb\s+([a-z][A-Za-z0-9_]*)\s*\(\s*"
    r"((?:[A-Z][A-Za-z0-9_]*|_)(?:\s*,\s*(?:[A-Z][A-Za-z0-9_]*|_))*)"
    r"\s*\)\s*\.\s*$"
)
_GLOBAL_DECLARATION = re.compile(r"#nherb\s*\.")
_LEGACY_VISIBILITY = re.compile(r"#(?:show|hide)\s+#nherb\b")
_SYMBOLIC_CONSTANT = re.compile(r"[a-z][A-Za-z0-9_]*")
_INTEGER = re.compile(r"-?\d+")
_FUNCTION_TERM = re.compile(r"([a-z][A-Za-z0-9_]*)\s*\(")
_ORDINARY_VARIABLE = re.compile(r"(?<![A-Za-z0-9_])([A-Z][A-Za-z0-9_]*)(?![A-Za-z0-9_])")
_NON_HERBRAND_VARIABLE = re.compile(r"(?<![A-Za-z0-9_])(_[A-Za-z0-9_]*)(?![A-Za-z0-9_])")
_VARIABLE = re.compile(r"(?<![A-Za-z0-9_])([A-Z][A-Za-z0-9_]*|_[A-Za-z0-9_]*)(?![A-Za-z0-9_])")
_RESERVED_IDENTIFIER = re.compile(r"(?<![A-Za-z0-9_])(__aspf_[A-Za-z0-9_]*)(?![A-Za-z0-9_])")

_DeclarationKey = tuple[str, int]


@dataclass(frozen=True, slots=True)
class _StatementContext:
    statement: ScannedStatement
    code: str
    executable: str
    points: dict[int, ScanPoint]


def parse_program(text: str, *, filename: str = "<string>") -> Program:
    """Parse and validate the supported compatibility slice."""

    return parse_sources((SourceText(text, filename),))


def parse_sources(sources: Sequence[SourceText]) -> Program:
    """Parse multiple sources with a shared declaration namespace."""

    prepared: list[tuple[SourceText, tuple[_StatementContext, ...], set[int]]] = []
    declarations: list[NHerbDeclaration] = []
    declared: set[_DeclarationKey] = set()
    for source in sources:
        scanned = split_statements(source)
        contexts = tuple(_context(statement) for statement in scanned)
        for context in contexts:
            _reject_reserved_identifier(context, source)
        source_declarations, declaration_indexes = _collect_declarations(contexts, source)
        for declaration in source_declarations:
            key = (declaration.name, declaration.arity)
            if key not in declared:
                declared.add(key)
                declarations.append(declaration)
        prepared.append((source, contexts, declaration_indexes))

    statements: list[ProgramStatement] = []
    for source_index, (source, contexts, declaration_indexes) in enumerate(prepared):
        for index, context in enumerate(contexts):
            if index in declaration_indexes:
                continue
            parsed = _parse_statement(context, source, declared)
            if parsed is not None:
                statements.append(parsed)
        if source_index + 1 < len(prepared) and not source.text.endswith("\n"):
            boundary = len(source.text)
            statements.append(OrdinaryStatement("\n", SourceSpan(boundary, boundary)))

    filename = sources[0].filename if len(sources) == 1 else "<multiple sources>"
    return Program(tuple(declarations), tuple(statements), filename)


def _context(statement: ScannedStatement) -> _StatementContext:
    return _StatementContext(
        statement=statement,
        code=executable_mask(statement.text, mask_strings=False),
        executable=executable_mask(statement.text),
        points={point.offset: point for point in scan_points(statement.text)},
    )


def _collect_declarations(
    contexts: tuple[_StatementContext, ...], source: SourceText
) -> tuple[list[NHerbDeclaration], set[int]]:
    declarations: list[NHerbDeclaration] = []
    indexes: set[int] = set()
    for index, context in enumerate(contexts):
        code = context.code
        visibility = _LEGACY_VISIBILITY.search(context.executable)
        if visibility:
            _unsupported(
                source,
                context,
                visibility.start(),
                "legacy '#show #nherb' and '#hide #nherb' directives are not supported",
            )
        global_match = _GLOBAL_DECLARATION.fullmatch(context.executable)
        if global_match:
            _unsupported(
                source,
                context,
                global_match.start(),
                "global '#nherb.' declarations are not supported; declare each function as "
                "'#nherb f/n.'",
            )
        match = _DECLARATION.fullmatch(code)
        application_match = _APPLICATION_DECLARATION.fullmatch(code)
        if not match and not application_match:
            if "#nherb" in context.executable:
                marker = context.executable.index("#nherb")
                _unsupported(
                    source,
                    context,
                    marker,
                    "unsupported #nherb declaration syntax; use '#nherb f/n.' or "
                    "placeholder-only '#nherb f(X,...).'",
                )
            continue
        if match:
            name = match.group(1)
            arity = int(match.group(2))
            local_start = match.start(1)
        else:
            assert application_match is not None
            name = application_match.group(1)
            arity = len(_split_arguments(application_match.group(2)))
            local_start = application_match.start(1)
        absolute_start = context.statement.span.start + local_start
        declarations.append(
            NHerbDeclaration(name, arity, SourceSpan(absolute_start, absolute_start + len(name)))
        )
        indexes.add(index)
    return declarations, indexes


def _parse_statement(
    context: _StatementContext, source: SourceText, declared: set[_DeclarationKey]
) -> ProgramStatement | None:
    text = context.statement.text
    if not text:
        return None

    visibility = _LEGACY_VISIBILITY.search(context.executable)
    if visibility:
        _unsupported(
            source,
            context,
            visibility.start(),
            "legacy '#show #nherb' and '#hide #nherb' directives are not supported",
        )

    operators = _find_n_atom_operators(context.executable)
    if not operators:
        return OrdinaryStatement(text, context.statement.span)

    separator = _find_top_level(context, ":-")
    n_atoms: list[NAtom] = []
    for operator_offset, comparison_operator in operators:
        point = context.points.get(operator_offset)
        if point is None:
            continue
        if point.brace_depth or point.bracket_depth:
            _unsupported(
                source,
                context,
                operator_offset,
                "n-atoms inside aggregates or choice constructs are not supported",
            )
        if point.paren_depth:
            _unsupported(
                source,
                context,
                operator_offset,
                "nested n-atoms are not supported",
            )
        is_body = separator is not None and operator_offset > separator
        n_atoms.append(
            _parse_n_atom(
                context,
                source,
                declared,
                operator_offset,
                comparison_operator,
                is_body,
                separator,
            )
        )

    parsed_n_atoms = tuple(n_atoms)
    _validate_n_atom_variable_safety(context, source, parsed_n_atoms, separator)
    return AspfStatement(text, context.statement.span, parsed_n_atoms)


def _reject_reserved_identifier(context: _StatementContext, source: SourceText) -> None:
    match = _RESERVED_IDENTIFIER.search(context.executable)
    if match:
        _unsupported(
            source,
            context,
            match.start(1),
            "identifiers beginning with '__aspf_' are reserved for aspf-next internals",
        )


def _find_n_atom_operators(executable: str) -> list[tuple[int, NAtomOperator]]:
    operators: list[tuple[int, NAtomOperator]] = []
    offset = 0
    ordered = sorted(NAtomOperator, key=lambda operator: len(operator.value), reverse=True)
    while offset < len(executable):
        matched = next(
            (operator for operator in ordered if executable.startswith(operator.value, offset)),
            None,
        )
        if matched is None:
            offset += 1
            continue
        operators.append((offset, matched))
        offset += len(matched.value)
    return operators


def _find_top_level(context: _StatementContext, needle: str) -> int | None:
    for offset, point in context.points.items():
        if point.paren_depth or point.bracket_depth or point.brace_depth:
            continue
        if context.executable.startswith(needle, offset):
            return offset
    return None


def _parse_n_atom(
    context: _StatementContext,
    source: SourceText,
    declared: set[_DeclarationKey],
    operator_offset: int,
    operator: NAtomOperator,
    is_body: bool,
    separator: int | None,
) -> NAtom:
    if operator is not NAtomOperator.EQUAL and not is_body:
        _unsupported(
            source,
            context,
            operator_offset,
            f"operator '{operator.value}' is supported only as a complete positive "
            "rule-body literal",
        )
    left = _parse_application_left(context, source, declared, operator_offset, operator)
    application_start = left.span.start - context.statement.span.start
    literal_start, literal_end = _literal_bounds(context, operator_offset, is_body, separator)
    if is_body:
        conditional_offset = next(
            (
                offset
                for offset, point in context.points.items()
                if operator_offset < offset < literal_end
                and context.statement.text[offset] == ":"
                and not (point.paren_depth or point.bracket_depth or point.brace_depth)
            ),
            None,
        )
        if conditional_offset is not None:
            _unsupported(
                source,
                context,
                operator_offset,
                "n-atoms inside conditional literals are not supported",
            )
    prefix = context.code[literal_start:application_start]
    prefix_code = prefix.strip()
    if prefix_code:
        if prefix_code == "not":
            _unsupported(
                source,
                context,
                literal_start + prefix.find("not"),
                "default-negated n-atoms are not supported",
            )
        _unsupported(
            source,
            context,
            application_start,
            "an n-atom must be a complete rule-head assignment or positive body literal",
        )

    value_start = _skip_space(context.code, operator_offset + len(operator.value), literal_end)
    value_end = _trim_code_end(context.code, value_start, literal_end)
    if value_start >= value_end:
        _unsupported(source, context, operator_offset, f"missing value after '{operator.value}'")
    right = _parse_right_operand(
        context,
        source,
        declared,
        value_start,
        value_end,
    )
    if not is_body and isinstance(right, ApplicationOperand):
        _unsupported(
            source,
            context,
            right.span.start - context.statement.span.start,
            "application-to-application comparison is supported only as a complete "
            "positive rule-body literal; a '#=' rule head remains a scalar assignment",
        )
    if (
        operator.is_ordered
        and isinstance(right, ScalarOperand)
        and right.kind is not GroundTermKind.INTEGER
    ):
        _unsupported(
            source,
            context,
            value_start,
            f"operator '{operator.value}' requires an integer literal on the right or a "
            "declared application",
        )

    if not is_body:
        head_start = _skip_space(
            context.code, 0, separator if separator is not None else literal_end
        )
        if head_start != application_start:
            _unsupported(
                source,
                context,
                application_start,
                "a supported '#=' rule head must consist only of the assignment",
            )
        if any(
            atom_offset != operator_offset
            for atom_offset, _operator in _find_n_atom_operators(context.executable[:literal_end])
        ):
            _unsupported(
                source,
                context,
                operator_offset,
                "multiple assignments in a rule head are unsupported",
            )

    absolute_start = context.statement.span.start + application_start
    absolute_end = context.statement.span.start + value_end
    span = SourceSpan(absolute_start, absolute_end)
    if is_body:
        return BodyComparison(left, right, operator, span)
    assert isinstance(right, ScalarOperand)
    return Assignment(left, right, span)


def _parse_application_left(
    context: _StatementContext,
    source: SourceText,
    declared: set[_DeclarationKey],
    operator_offset: int,
    operator: NAtomOperator,
) -> ApplicationOperand:
    end = _trim_code_end(context.code, 0, operator_offset)
    if end <= 0:
        _unsupported(
            source,
            context,
            operator_offset,
            f"left side of '{operator.value}' must be a declared function application",
        )
    if context.code[end - 1] != ")":
        name_start = end
        while name_start > 0 and (
            context.code[name_start - 1].isalnum() or context.code[name_start - 1] == "_"
        ):
            name_start -= 1
        return _parse_application_operand(
            context,
            source,
            declared,
            name_start,
            end,
            side=f"left side of '{operator.value}'",
        )

    open_paren = _matching_open_paren(context.code, end - 1)
    if open_paren is None:
        _unsupported(
            source,
            context,
            operator_offset,
            f"unbalanced function application before '{operator.value}'",
        )
    name_end = _trim_code_end(context.code, 0, open_paren)
    name_start = name_end
    while name_start > 0 and (
        context.code[name_start - 1].isalnum() or context.code[name_start - 1] == "_"
    ):
        name_start -= 1
    return _parse_application_operand(
        context,
        source,
        declared,
        name_start,
        end,
        side=f"left side of '{operator.value}'",
    )


def _parse_right_operand(
    context: _StatementContext,
    source: SourceText,
    declared: set[_DeclarationKey],
    start: int,
    end: int,
) -> ComparisonOperand:
    code = context.code[start:end]
    stripped = code.strip()
    term_start = start + (len(code) - len(code.lstrip()))
    term_end = term_start + len(stripped)
    if _SYMBOLIC_CONSTANT.fullmatch(stripped) and (stripped, 0) in declared:
        return _parse_application_operand(
            context, source, declared, term_start, term_end, side="right operand"
        )

    function_match = _FUNCTION_TERM.match(stripped)
    if function_match and stripped.endswith(")"):
        open_offset = stripped.find("(")
        if _matching_open_paren(stripped, len(stripped) - 1) == open_offset:
            argument_ranges = _split_argument_ranges(stripped, open_offset + 1, len(stripped) - 1)
            if (function_match.group(1), len(argument_ranges)) in declared:
                return _parse_application_operand(
                    context, source, declared, term_start, term_end, side="right operand"
                )

    term = _parse_ground_term(
        context.statement.text[start:end],
        context=context,
        source=source,
        local_offset=start,
        declared=declared,
        as_value=True,
    )
    absolute_start = context.statement.span.start + term_start
    return ScalarOperand(term, SourceSpan(absolute_start, absolute_start + len(stripped)))


def _parse_application_operand(
    context: _StatementContext,
    source: SourceText,
    declared: set[_DeclarationKey],
    start: int,
    end: int,
    *,
    side: str,
) -> ApplicationOperand:
    start = _skip_space(context.code, start, end)
    end = _trim_code_end(context.code, start, end)
    text = context.code[start:end]
    if _SYMBOLIC_CONSTANT.fullmatch(text):
        name = text
        argument_ranges: list[tuple[int, int]] = []
    else:
        match = _FUNCTION_TERM.match(text)
        if match is None or not text.endswith(")"):
            _unsupported(
                source,
                context,
                start,
                f"{side} must be a declared function application",
            )
        open_offset = text.find("(")
        if _matching_open_paren(text, len(text) - 1) != open_offset:
            _unsupported(
                source,
                context,
                start,
                f"{side} must be one complete declared function application",
            )
        name = match.group(1)
        argument_ranges = _split_argument_ranges(text, open_offset + 1, len(text) - 1)

    arity = len(argument_ranges)
    if (name, arity) not in declared:
        declared_arities = sorted(
            item_arity for item_name, item_arity in declared if item_name == name
        )
        if not declared_arities:
            _unsupported(source, context, start, f"non-Herbrand function '{name}' is not declared")
        rendered_arities = ", ".join(str(item) for item in declared_arities)
        _unsupported(
            source,
            context,
            start,
            f"non-Herbrand function '{name}/{arity}' is not declared; declared arities: "
            f"{rendered_arities}",
        )
    arguments = [
        _parse_application_argument(
            text[argument_start:argument_end],
            context=context,
            source=source,
            local_offset=start + argument_start,
            declared=declared,
        )
        for argument_start, argument_end in argument_ranges
    ]
    absolute_start = context.statement.span.start + start
    application = FunctionApplication(name, tuple(arguments))
    return ApplicationOperand(application, SourceSpan(absolute_start, absolute_start + len(text)))


def _parse_application_argument(
    text: str,
    *,
    context: _StatementContext,
    source: SourceText,
    local_offset: int,
    declared: set[_DeclarationKey],
) -> ApplicationArgument:
    stripped = text.strip()
    term_offset = local_offset + (len(text) - len(text.lstrip()))
    if _ORDINARY_VARIABLE.fullmatch(stripped):
        absolute_start = context.statement.span.start + term_offset
        return VariableTerm(
            stripped,
            SourceSpan(absolute_start, absolute_start + len(stripped)),
        )

    executable = executable_mask(stripped)
    variable = _VARIABLE.search(executable)
    if variable:
        variable_name = variable.group(1)
        variable_offset = term_offset + variable.start(1)
        if variable_name == "_":
            _unsupported(
                source,
                context,
                variable_offset,
                "anonymous variables are not supported inside n-atoms",
            )
        if _NON_HERBRAND_VARIABLE.fullmatch(variable_name):
            _unsupported(
                source,
                context,
                variable_offset,
                f"non-Herbrand variables such as '{variable_name}' are not supported by "
                "the reference backend",
            )
        _unsupported(
            source,
            context,
            variable_offset,
            "variables are supported only as complete direct arguments of a "
            "non-Herbrand application",
        )

    return _parse_ground_term(
        text,
        context=context,
        source=source,
        local_offset=local_offset,
        declared=declared,
        as_value=False,
    )


def _validate_n_atom_variable_safety(
    context: _StatementContext,
    source: SourceText,
    n_atoms: tuple[NAtom, ...],
    separator: int | None,
) -> None:
    variables = sorted(
        (
            argument
            for n_atom in n_atoms
            for operand in _application_operands(n_atom)
            for argument in operand.application.arguments
            if isinstance(argument, VariableTerm)
        ),
        key=lambda variable: variable.span.start,
    )
    if not variables:
        return

    domain_variables = _ordinary_domain_variables(context, n_atoms, separator)
    checked: set[str] = set()
    for variable in variables:
        if variable.name in checked:
            continue
        checked.add(variable.name)
        if variable.name in domain_variables:
            continue
        local_offset = variable.span.start - context.statement.span.start
        _unsupported(
            source,
            context,
            local_offset,
            f"variable '{variable.name}' in a non-Herbrand application must occur in an "
            "ordinary positive body atom in the same rule",
        )


def _ordinary_domain_variables(
    context: _StatementContext,
    n_atoms: tuple[NAtom, ...],
    separator: int | None,
) -> set[str]:
    if separator is None:
        return set()

    result: set[str] = set()
    n_atom_starts = {
        n_atom.span.start - context.statement.span.start
        for n_atom in n_atoms
        if isinstance(n_atom, BodyComparison)
    }
    for start, end in _body_literal_ranges(context, separator):
        if any(start <= n_atom_start < end for n_atom_start in n_atom_starts):
            continue
        atom_bounds = _positive_symbolic_atom_bounds(context.executable, start, end)
        if atom_bounds is None:
            continue
        atom_start, atom_end = atom_bounds
        result.update(
            match.group(1)
            for match in _ORDINARY_VARIABLE.finditer(context.executable, atom_start, atom_end)
        )
    return result


def _body_literal_ranges(context: _StatementContext, separator: int) -> tuple[tuple[int, int], ...]:
    start = separator + 2
    end = _statement_period(context)
    ranges: list[tuple[int, int]] = []
    for offset, point in context.points.items():
        if not start <= offset < end:
            continue
        if point.paren_depth or point.bracket_depth or point.brace_depth:
            continue
        if context.statement.text[offset] in {",", ";"}:
            ranges.append((start, offset))
            start = offset + 1
    ranges.append((start, end))
    return tuple(ranges)


def _positive_symbolic_atom_bounds(executable: str, start: int, end: int) -> tuple[int, int] | None:
    atom_start = _skip_space(executable, start, end)
    atom_end = _trim_code_end(executable, atom_start, end)
    if atom_start >= atom_end:
        return None

    predicate = _SYMBOLIC_CONSTANT.match(executable, atom_start, atom_end)
    if predicate is None:
        return None
    cursor = _skip_space(executable, predicate.end(), atom_end)
    if cursor == atom_end:
        return atom_start, atom_end
    if executable[cursor] != "(" or executable[atom_end - 1] != ")":
        return None
    if _matching_open_paren(executable, atom_end - 1) != cursor:
        return None
    return atom_start, atom_end


def _literal_bounds(
    context: _StatementContext,
    operator_offset: int,
    is_body: bool,
    separator: int | None,
) -> tuple[int, int]:
    if not is_body:
        end = separator if separator is not None else _statement_period(context)
        return 0, end

    assert separator is not None
    start = separator + 2
    end = _statement_period(context)
    for offset, point in context.points.items():
        if point.paren_depth or point.bracket_depth or point.brace_depth:
            continue
        char = context.statement.text[offset]
        if char in {",", ";"}:
            if offset < operator_offset:
                start = offset + 1
            elif offset > operator_offset:
                end = offset
                break
    return start, end


def _statement_period(context: _StatementContext) -> int:
    for offset in range(len(context.statement.text) - 1, -1, -1):
        point = context.points.get(offset)
        if (
            point
            and context.statement.text[offset] == "."
            and not (point.paren_depth or point.bracket_depth or point.brace_depth)
        ):
            return offset
    return len(context.statement.text)


def _matching_open_paren(code: str, close_offset: int) -> int | None:
    depth = 0
    for offset in range(close_offset, -1, -1):
        char = code[offset]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
            if depth == 0:
                return offset
    return None


def _split_arguments(text: str) -> list[str]:
    if not text.strip():
        return []
    parts: list[str] = []
    start = 0
    for point in scan_points(text):
        if text[point.offset] == "," and not (
            point.paren_depth or point.bracket_depth or point.brace_depth
        ):
            parts.append(text[start : point.offset].strip())
            start = point.offset + 1
    parts.append(text[start:].strip())
    return parts


def _split_argument_ranges(text: str, start: int, end: int) -> list[tuple[int, int]]:
    if not text[start:end].strip():
        return []
    ranges: list[tuple[int, int]] = []
    part_start = start
    for point in scan_points(text):
        if not start <= point.offset < end:
            continue
        if (
            text[point.offset] == ","
            and point.paren_depth == 1
            and not (point.bracket_depth or point.brace_depth)
        ):
            ranges.append(_trim_argument_range(text, part_start, point.offset))
            part_start = point.offset + 1
    ranges.append(_trim_argument_range(text, part_start, end))
    return ranges


def _trim_argument_range(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _application_operands(n_atom: NAtom) -> tuple[ApplicationOperand, ...]:
    if isinstance(n_atom, Assignment):
        return (n_atom.target,)
    if isinstance(n_atom.right, ApplicationOperand):
        return n_atom.left, n_atom.right
    return (n_atom.left,)


def _parse_ground_term(
    text: str,
    *,
    context: _StatementContext,
    source: SourceText,
    local_offset: int,
    declared: set[_DeclarationKey],
    as_value: bool,
) -> GroundTerm:
    stripped = text.strip()
    term_offset = local_offset + (len(text) - len(text.lstrip()))
    variable = _VARIABLE.search(executable_mask(stripped))
    if variable:
        variable_name = variable.group(1)
        variable_offset = term_offset + variable.start(1)
        if variable_name == "_":
            _unsupported(
                source,
                context,
                variable_offset,
                "anonymous variables are not supported inside n-atoms",
            )
        if _NON_HERBRAND_VARIABLE.fullmatch(variable_name):
            _unsupported(
                source,
                context,
                variable_offset,
                f"non-Herbrand variables such as '{variable_name}' are not supported by "
                "the reference backend",
            )
        message = (
            "variables as n-atom values are not supported in the first variable milestone"
            if as_value
            else "variables are supported only as complete direct arguments of a "
            "non-Herbrand application"
        )
        _unsupported(
            source,
            context,
            variable_offset,
            message,
        )
    if _INTEGER.fullmatch(stripped):
        return GroundTerm(stripped, GroundTermKind.INTEGER)
    if _SYMBOLIC_CONSTANT.fullmatch(stripped):
        if (stripped, 0) in declared:
            message = (
                "a declared non-Herbrand application cannot be used as the value of another "
                "non-Herbrand application"
                if as_value
                else "nested declared non-Herbrand applications are not supported"
            )
            _unsupported(source, context, term_offset, message)
        return GroundTerm(stripped, GroundTermKind.SYMBOL)
    if _is_string(stripped):
        return GroundTerm(stripped, GroundTermKind.STRING)

    function_match = _FUNCTION_TERM.match(stripped)
    if function_match and stripped.endswith(")"):
        function_name = function_match.group(1)
        open_offset = stripped.find("(")
        if _matching_open_paren(stripped, len(stripped) - 1) != open_offset:
            _unsupported(
                source,
                context,
                term_offset,
                "arithmetic or unsupported term syntax inside n-atoms is not supported",
            )
        argument_ranges = _split_argument_ranges(stripped, open_offset + 1, len(stripped) - 1)
        if (function_name, len(argument_ranges)) in declared:
            message = (
                "a declared non-Herbrand application cannot be used as the value of another "
                "non-Herbrand application"
                if as_value
                else "nested declared non-Herbrand applications are not supported"
            )
            _unsupported(source, context, term_offset, message)
        for argument_start, argument_end in argument_ranges:
            _parse_ground_term(
                stripped[argument_start:argument_end],
                context=context,
                source=source,
                local_offset=term_offset + argument_start,
                declared=declared,
                as_value=as_value,
            )
        return GroundTerm(stripped, GroundTermKind.FUNCTION)

    _unsupported(
        source,
        context,
        term_offset,
        "arithmetic or unsupported term syntax inside n-atoms is not supported",
    )


def _is_string(text: str) -> bool:
    if len(text) < 2 or text[0] != '"' or text[-1] != '"':
        return False
    escaped = False
    for char in text[1:-1]:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return False
    return not escaped


def _skip_space(code: str, start: int, end: int) -> int:
    while start < end and code[start].isspace():
        start += 1
    return start


def _trim_code_end(code: str, start: int, end: int) -> int:
    while end > start and code[end - 1].isspace():
        end -= 1
    return end


def _unsupported(
    source: SourceText, context: _StatementContext, local_offset: int, message: str
) -> Never:
    absolute_offset = context.statement.span.start + local_offset
    raise UnsupportedSyntaxError(message, source.location(absolute_offset))
