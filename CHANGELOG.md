# Changelog

Notable changes to ASPf-next are recorded here. The project uses
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) structure and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) for reader-facing
releases. Python package metadata uses the equivalent PEP 440 version.

## Unreleased

No changes yet.

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
