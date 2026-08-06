# ASP{f}-next first-milestone plan

## Scope

Build an independent, clean-room Python 3.11+ compatibility frontend for the
restricted ASP{f} vertical slice in the project brief. The implementation will
use the public Python API of Clingo 5.8 and will not modify Clingo or copy code
from historical Clingo{f}.

## Proposed changes

1. Add package and tooling metadata:
   - `pyproject.toml` with Clingo, pytest, Ruff, and mypy configuration.
   - `LICENSE` using the repository's MIT licensing convention.
   - a console entry point named `aspf`.
2. Add a typed `src/aspf_next` package with separate responsibilities:
   - `source.py`: source locations, spans, scanner state, and statement splitting.
   - `errors.py`: location-aware frontend diagnostics.
   - `ir.py`: immutable declarations, ordinary statements, n-atoms, and rules.
   - `frontend.py`: context-aware parsing and validation of the supported slice.
   - `lowering.py`: reference translation to `__aspf_value/2` plus functionality.
   - `solver.py`: Clingo 5.8 control, grounding, and model enumeration.
   - `model.py`: stable normalized human and JSON model rendering.
   - `cli.py`: file loading, `--models`, `--emit-lowered`, and `--json`.
3. Add tests for parsing, lowering, solving, rendering, CLI behavior, multiline
   input, comments, pass-through ASP, and every explicitly unsupported form.
4. Add runnable examples for basic, conditional, and conflicting assignments.
5. Add documentation covering architecture, supported syntax, semantics,
   compatibility limits, and clean-room provenance.

## Implementation sequence

1. Scaffold metadata, errors, source scanner, IR, and frontend tests.
2. Implement reference lowering with tests.
3. Add Clingo integration, rendering, CLI, examples, and end-to-end tests.
4. Complete user documentation and provenance notes.
5. Run formatting, linting, strict static checks, and the complete test suite.

Each completed stage will be committed separately.

## Parsing design

The frontend will use a character scanner rather than global substitutions. It
will track filename, line, column, comments, escaped quoted strings, and nesting
depth for parentheses, brackets, and braces. Only top-level statement boundaries
and top-level rule/body separators will be recognized. Ordinary statements with
no ASP{f} marker will be preserved byte-for-byte apart from the enclosing source
assembly needed for Clingo.

Supported n-atoms will be parsed into structured IR. Function applications and
values are deliberately ground: any variable or arithmetic-shaped term in an
n-atom will fail before lowering. The scanner will reject n-atoms in aggregates
and default-negated contexts with a location-aware `UnsupportedSyntaxError`.

## Initial semantic decisions

- `#nherb f/n.` is a declaration only and emits no Clingo statement.
- Every lowered assignment or positive comparison uses
  `__aspf_value(f(args), value)`.
- A single global functionality constraint is appended whenever the program has
  at least one non-Herbrand declaration.
- No totality rule is generated; undefined applications remain absent.
- Model rendering combines Clingo's shown ordinary atoms with all true internal
  value atoms, filters every other `__aspf_` atom, and sorts the result for stable
  output.
- If the input contains `#show`, Clingo controls which ordinary atoms are shown,
  while ASP{f} assignments are still reconstructed from internal atoms.
- Redeclaring the same `f/n` is accepted, but using the same name with a different
  arity or using an undeclared application in an n-atom is diagnosed.
- Executable identifiers beginning with `__aspf_` are reserved for backend use.
- A declared non-Herbrand symbol may occur only in a validated supported n-atom.

## Design concerns and boundaries

- The first backend is a semantic reference translation, not an efficiency claim
  and not a native propagator.
- Clingo lexical syntax is broad. This milestone validates terms conservatively;
  ambiguous n-atom terms are rejected instead of assigned invented semantics.
- `#=` inside comments and strings is inert. Unsupported operators are diagnosed
  only in executable syntax.
- Aggregates are passed through only when they contain no n-atoms.
- Ordinary Clingo parsing remains Clingo's responsibility after the compatibility
  frontend has preserved or lowered each statement.
- Native theory atoms, custom propagators, arithmetic, aggregates containing
  n-atoms, and trading examples are explicitly deferred.
