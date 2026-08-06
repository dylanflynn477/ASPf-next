"""Compatibility-first ASP{f} frontend for modern Clingo."""

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program, parse_sources
from aspf_next.ir import Program

__all__ = ["Program", "UnsupportedSyntaxError", "parse_program", "parse_sources"]
__version__ = "0.1.0"
