# Changelog

Notable changes to ASPf-next are recorded here. The project uses
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) structure and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) for reader-facing
releases. Python package metadata uses the equivalent PEP 440 version.

## Unreleased

### Added

- Primary-source traceability for every milestone 0.1 construct and known
  compatibility deviation.
- A manifest-driven conformance corpus covering accepted and rejected syntax,
  solving behavior, partiality, functionality, model enumeration, source
  layout, and multiple files.
- Architecture decision records for clean-room development, reference
  lowering, partiality, conservative rejection, and the private backend
  namespace.
- Positive, ground `#!=` comparisons as complete rule-body literals. The left
  application must be defined, and its value must differ from the restricted
  ground right operand.
- Typed comparison operators in the ASP{f} IR and definedness-aware reference
  lowering through an explicit value lookup.
- Focused frontend, lowering, solver, CLI, and conformance regressions for
  inequality behavior and its unsupported contexts.
- Positive, fully ground `#<`, `#<=`, `#>`, and `#>=` comparisons as complete
  rule-body literals with integer literals on the right.
- Definedness- and type-aware reference lowering that tags integer assignment
  values before applying a shared ordinary comparison path.
- Ordered-comparison conformance fixtures, CLI regressions, and a sixth guided
  example covering negative, zero, and positive values.
- Typed ordinary variables in direct non-Herbrand application arguments, with
  source spans and a conservative source-level domain-safety check.
- Domain-safe variable lowering for assignment heads and all six supported body
  operators while keeping every right operand ground.
- Focused frontend, lowering, solver, CLI, and conformance regressions plus a
  seventh guided example for restricted ordinary variables.

No release number has been assigned to these development increments.

## 0.1.0-alpha - Unreleased

### Added

- Location-aware scanning for comments, strings, multiline statements, and
  nested delimiters.
- A restricted compatibility frontend for `#nherb f/n.`, ground `#=` head
  assignments, and positive ground body comparisons.
- Typed ASP{f} intermediate representations and an inspectable reference
  translation to `__aspf_value/2` with a functionality constraint.
- Clingo 5.8 solving, model enumeration, stable ASP{f}-style reconstruction,
  JSON output, and lowered-source output.
- Explicit diagnostics for deferred syntax and reserved internal identifiers.
- Guided examples, tutorial, reproducible terminal demos, architecture and
  provenance documentation, and Python 3.11/3.12 CI.

### Known limitations

The release does not implement inequalities, default-negated n-atoms,
arithmetic inside n-atoms, variables inside n-atoms, n-atoms in aggregates or
choices, or a native theory-atom/propagator backend. It does not claim full
historical ASP{f} compatibility.
