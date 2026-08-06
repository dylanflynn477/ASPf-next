"""Public exception types for the compatibility frontend."""

from __future__ import annotations

from aspf_next.source import SourceLocation


class AspfNextError(Exception):
    """Base class for expected user-facing errors."""


class UnsupportedSyntaxError(AspfNextError):
    """Syntax that is outside the currently supported compatibility slice."""

    def __init__(self, message: str, location: SourceLocation) -> None:
        self.message = message
        self.location = location
        super().__init__(f"{location}: {message}")


class SolverError(AspfNextError):
    """Clingo could not parse, ground, or solve a lowered program."""
