"""Compatibility parser for the deliberately restricted ASP{f} milestone."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Never

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.ir import (
    AspfStatement,
    FunctionApplication,
    GroundTerm,
    NAtom,
    NAtomRole,
    NHerbDeclaration,
    OrdinaryStatement,
    Program,
    ProgramStatement,
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
_GLOBAL_DECLARATION = re.compile(r"#nherb\s*\.")
_LEGACY_VISIBILITY = re.compile(r"#(?:show|hide)\s+#nherb\b")
_SYMBOLIC_CONSTANT = re.compile(r"[a-z][A-Za-z0-9_]*")
_INTEGER = re.compile(r"-?\d+")
_FUNCTION_TERM = re.compile(r"([a-z][A-Za-z0-9_]*)\s*\(")
_VARIABLE = re.compile(r"(?:\b[A-Z][A-Za-z0-9_]*\b|\b_[A-Za-z0-9_]*\b)")
_UNSUPPORTED_OPERATORS = ("#!=", "#<=", "#>=", "#<", "#>")


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
    declared: dict[str, int] = {}
    for source in sources:
        scanned = split_statements(source)
        contexts = tuple(_context(statement) for statement in scanned)
        source_declarations, declaration_indexes = _collect_declarations(contexts, source)
        for declaration in source_declarations:
            previous_arity = declared.get(declaration.name)
            if previous_arity is not None and previous_arity != declaration.arity:
                raise UnsupportedSyntaxError(
                    f"non-Herbrand function '{declaration.name}' was already declared with "
                    f"arity {previous_arity}",
                    source.location(declaration.span.start),
                )
            declared[declaration.name] = declaration.arity
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
    declared: dict[str, int] = {}
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
        if not match:
            if "#nherb" in context.executable:
                marker = context.executable.index("#nherb")
                _unsupported(source, context, marker, "unsupported #nherb declaration syntax")
            continue
        name = match.group(1)
        arity = int(match.group(2))
        if name in declared and declared[name] != arity:
            _unsupported(
                source,
                context,
                match.start(1),
                f"non-Herbrand function '{name}' was already declared with arity {declared[name]}",
            )
        declared[name] = arity
        local_start = match.start(1)
        absolute_start = context.statement.span.start + local_start
        declarations.append(
            NHerbDeclaration(name, arity, SourceSpan(absolute_start, absolute_start + len(name)))
        )
        indexes.add(index)
    return declarations, indexes


def _parse_statement(
    context: _StatementContext, source: SourceText, declared: dict[str, int]
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

    for operator in _UNSUPPORTED_OPERATORS:
        offset = context.executable.find(operator)
        if offset >= 0:
            _unsupported(
                source,
                context,
                offset,
                f"operator '{operator}' is not supported in the first milestone; only '#=' is",
            )

    equality_offsets = _find_equalities(context.executable)
    if not equality_offsets:
        return OrdinaryStatement(text, context.statement.span)

    separator = _find_top_level(context, ":-")
    n_atoms: list[NAtom] = []
    for operator_offset in equality_offsets:
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
        role = (
            NAtomRole.BODY
            if separator is not None and operator_offset > separator
            else NAtomRole.HEAD
        )
        n_atoms.append(_parse_n_atom(context, source, declared, operator_offset, role, separator))

    return AspfStatement(text, context.statement.span, tuple(n_atoms))


def _find_equalities(executable: str) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        offset = executable.find("#=", start)
        if offset < 0:
            return offsets
        following = executable[offset + 2 : offset + 3]
        if following in {"=", "<", ">", "!"}:
            # It is still ASP{f}-shaped but not a supported exact operator.
            offsets.append(offset)
        else:
            offsets.append(offset)
        start = offset + 2


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
    declared: dict[str, int],
    operator_offset: int,
    role: NAtomRole,
    separator: int | None,
) -> NAtom:
    application_start, _application_end, name, arguments = _parse_application_left(
        context, source, declared, operator_offset
    )
    literal_start, literal_end = _literal_bounds(context, operator_offset, role, separator)
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

    value_start = _skip_space(context.code, operator_offset + 2, literal_end)
    value_end = _trim_code_end(context.code, value_start, literal_end)
    if value_start >= value_end:
        _unsupported(source, context, operator_offset, "missing value after '#='")
    value_text = context.statement.text[value_start:value_end]
    value = _parse_ground_term(
        value_text,
        context=context,
        source=source,
        local_offset=value_start,
        declared=declared,
        as_value=True,
    )

    if role is NAtomRole.HEAD:
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
            for atom_offset in _find_equalities(context.executable[:literal_end])
        ):
            _unsupported(
                source,
                context,
                operator_offset,
                "multiple assignments in a rule head are unsupported",
            )

    absolute_start = context.statement.span.start + application_start
    absolute_end = context.statement.span.start + value_end
    application = FunctionApplication(name, tuple(arguments))
    return NAtom(application, value, role, SourceSpan(absolute_start, absolute_end))


def _parse_application_left(
    context: _StatementContext,
    source: SourceText,
    declared: dict[str, int],
    operator_offset: int,
) -> tuple[int, int, str, list[GroundTerm]]:
    end = _trim_code_end(context.code, 0, operator_offset)
    if end <= 0:
        _unsupported(
            source,
            context,
            operator_offset,
            "left side of '#=' must be a declared function application",
        )
    if context.code[end - 1] != ")":
        name_start = end
        while name_start > 0 and (
            context.code[name_start - 1].isalnum() or context.code[name_start - 1] == "_"
        ):
            name_start -= 1
        name = context.code[name_start:end]
        if not _SYMBOLIC_CONSTANT.fullmatch(name):
            _unsupported(
                source,
                context,
                name_start,
                "left side of '#=' must be a declared function application",
            )
        if name not in declared:
            _unsupported(
                source, context, name_start, f"non-Herbrand function '{name}' is not declared"
            )
        if declared[name] != 0:
            _unsupported(
                source,
                context,
                name_start,
                f"non-Herbrand function '{name}' expects {declared[name]} argument(s), got 0",
            )
        return name_start, end, name, []

    open_paren = _matching_open_paren(context.code, end - 1)
    if open_paren is None:
        _unsupported(
            source, context, operator_offset, "unbalanced function application before '#='"
        )
    name_end = _trim_code_end(context.code, 0, open_paren)
    name_start = name_end
    while name_start > 0 and (
        context.code[name_start - 1].isalnum() or context.code[name_start - 1] == "_"
    ):
        name_start -= 1
    name = context.code[name_start:name_end]
    if not _SYMBOLIC_CONSTANT.fullmatch(name):
        _unsupported(
            source,
            context,
            name_start,
            "left side of '#=' must use a lowercase declared function name",
        )
    if name not in declared:
        _unsupported(source, context, name_start, f"non-Herbrand function '{name}' is not declared")

    arguments_text = context.code[open_paren + 1 : end - 1]
    argument_parts = _split_arguments(arguments_text)
    if len(argument_parts) != declared[name]:
        _unsupported(
            source,
            context,
            name_start,
            f"non-Herbrand function '{name}' expects {declared[name]} argument(s), "
            f"got {len(argument_parts)}",
        )
    arguments: list[GroundTerm] = []
    search_start = open_paren + 1
    for part in argument_parts:
        relative = context.code.find(part, search_start, end - 1)
        arguments.append(
            _parse_ground_term(
                part,
                context=context,
                source=source,
                local_offset=relative,
                declared=declared,
                as_value=False,
            )
        )
        search_start = relative + len(part)
    return name_start, end, name, arguments


def _literal_bounds(
    context: _StatementContext,
    operator_offset: int,
    role: NAtomRole,
    separator: int | None,
) -> tuple[int, int]:
    if role is NAtomRole.HEAD:
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


def _parse_ground_term(
    text: str,
    *,
    context: _StatementContext,
    source: SourceText,
    local_offset: int,
    declared: dict[str, int],
    as_value: bool,
) -> GroundTerm:
    stripped = text.strip()
    term_offset = local_offset + (len(text) - len(text.lstrip()))
    if _VARIABLE.search(executable_mask(stripped)):
        _unsupported(
            source,
            context,
            term_offset,
            "variables, including non-Herbrand variables, are not supported inside n-atoms",
        )
    if _INTEGER.fullmatch(stripped) or _SYMBOLIC_CONSTANT.fullmatch(stripped):
        return GroundTerm(stripped)
    if _is_string(stripped):
        return GroundTerm(stripped)

    function_match = _FUNCTION_TERM.match(stripped)
    if function_match and stripped.endswith(")"):
        function_name = function_match.group(1)
        if function_name in declared:
            message = (
                "a declared non-Herbrand application cannot be used as the value of another "
                "non-Herbrand application"
                if as_value
                else "nested declared non-Herbrand applications are not supported"
            )
            _unsupported(source, context, term_offset, message)
        if as_value:
            _unsupported(
                source,
                context,
                term_offset,
                "only integer, symbolic constant, and string values are supported",
            )
        open_offset = stripped.find("(")
        if _matching_open_paren(stripped, len(stripped) - 1) == open_offset:
            for part in _split_arguments(stripped[open_offset + 1 : -1]):
                _parse_ground_term(
                    part,
                    context=context,
                    source=source,
                    local_offset=term_offset + open_offset + 1,
                    declared=declared,
                    as_value=as_value,
                )
            return GroundTerm(stripped)

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
