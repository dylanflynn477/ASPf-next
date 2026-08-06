"""Location-aware scanning primitives for legacy ASP{f} source."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum, auto


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """A one-based location in a named source."""

    filename: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.column}"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """A half-open character span in a source."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class ScannedStatement:
    """A top-level statement and its absolute source span."""

    text: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ScanPoint:
    """Lexical context at an executable source character."""

    offset: int
    paren_depth: int
    bracket_depth: int
    brace_depth: int


class _Mode(Enum):
    CODE = auto()
    STRING = auto()
    LINE_COMMENT = auto()
    BLOCK_COMMENT = auto()


@dataclass(frozen=True, slots=True)
class SourceText:
    """Source content with efficient offset-to-line conversion."""

    text: str
    filename: str = "<string>"
    _newline_offsets: tuple[int, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        newline_offsets = tuple(index for index, char in enumerate(self.text) if char == "\n")
        object.__setattr__(self, "_newline_offsets", newline_offsets)

    def location(self, offset: int) -> SourceLocation:
        """Return a one-based location, clamping the offset to the source."""

        safe_offset = max(0, min(offset, len(self.text)))
        line_index = bisect_right(self._newline_offsets, safe_offset - 1)
        previous_newline = self._newline_offsets[line_index - 1] if line_index else -1
        return SourceLocation(self.filename, line_index + 1, safe_offset - previous_newline)


def scan_points(text: str) -> Iterator[ScanPoint]:
    """Yield executable characters with their nesting context.

    Comment contents and quoted-string contents are not executable. The opening
    quote is yielded so callers can identify a string term; the rest of that
    string, including its closing quote, is deliberately skipped.
    """

    mode = _Mode.CODE
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if mode is _Mode.LINE_COMMENT:
            if char == "\n":
                mode = _Mode.CODE
            index += 1
            continue
        if mode is _Mode.BLOCK_COMMENT:
            if char == "*" and next_char == "%":
                mode = _Mode.CODE
                index += 2
            else:
                index += 1
            continue
        if mode is _Mode.STRING:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                mode = _Mode.CODE
            index += 1
            continue

        if char == "%" and next_char == "*":
            mode = _Mode.BLOCK_COMMENT
            index += 2
            continue
        if char == "%":
            mode = _Mode.LINE_COMMENT
            index += 1
            continue

        yield ScanPoint(index, paren_depth, bracket_depth, brace_depth)

        if char == '"':
            mode = _Mode.STRING
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth = max(0, brace_depth - 1)
        index += 1


def executable_mask(text: str, *, mask_strings: bool = True) -> str:
    """Mask comments and optionally string contents while preserving offsets."""

    visible = [False] * len(text)
    for point in scan_points(text):
        visible[point.offset] = True

    if not mask_strings:
        mode = _Mode.CODE
        escaped = False
        index = 0
        while index < len(text):
            char = text[index]
            next_char = text[index + 1] if index + 1 < len(text) else ""
            if mode is _Mode.LINE_COMMENT:
                if char == "\n":
                    mode = _Mode.CODE
                index += 1
                continue
            if mode is _Mode.BLOCK_COMMENT:
                if char == "*" and next_char == "%":
                    mode = _Mode.CODE
                    index += 2
                else:
                    index += 1
                continue
            if mode is _Mode.STRING:
                visible[index] = True
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    mode = _Mode.CODE
                index += 1
                continue
            if char == "%" and next_char == "*":
                mode = _Mode.BLOCK_COMMENT
                index += 2
                continue
            if char == "%":
                mode = _Mode.LINE_COMMENT
                index += 1
                continue
            if char == '"':
                mode = _Mode.STRING
            index += 1

    return "".join(
        char if visible[index] or char == "\n" else " " for index, char in enumerate(text)
    )


def split_statements(source: SourceText) -> tuple[ScannedStatement, ...]:
    """Split on top-level statement periods, retaining comments and whitespace."""

    statements: list[ScannedStatement] = []
    start = 0
    points = {point.offset: point for point in scan_points(source.text)}
    for offset, point in points.items():
        if source.text[offset] != ".":
            continue
        if point.paren_depth or point.bracket_depth or point.brace_depth:
            continue
        previous = source.text[offset - 1] if offset else ""
        following = source.text[offset + 1] if offset + 1 < len(source.text) else ""
        if previous == "." or following == ".":
            continue
        end = offset + 1
        statements.append(ScannedStatement(source.text[start:end], SourceSpan(start, end)))
        start = end

    if start < len(source.text):
        statements.append(
            ScannedStatement(source.text[start:], SourceSpan(start, len(source.text)))
        )
    return tuple(statements)
