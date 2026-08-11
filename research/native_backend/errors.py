"""Diagnostics for the isolated native-backend experiment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NativeValidationError(ValueError):
    """A location-aware violation of the experimental semantic contract."""

    message: str
    filename: str = "<research>"
    line: int = 1
    column: int = 1

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.column}: {self.message}"
