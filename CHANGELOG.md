# Changelog

Notable changes to ASPf-next are recorded here. Reader-facing and Python
package versions use the same PEP 440 spelling.

## Unreleased

### Added

- Added `aspf --version` and a wheel-install smoke check in CI.

### Research

- Retained solver-literal support provenance for native research values, n-variable
  definitions, comparisons, and guards; derived functionality conflicts and guard
  mismatches can now receive narrow clauses.
- Added early research-propagator evaluation, static undefinedness proofs, thread-local
  learned-clause/evaluation caches with exact invalidation, explanation diagnostics,
  and deterministic work counters.
- Preserved exact reference/native models while eliminating broad clauses from the
  recorded multi-application workload. The native backend remains research-only and
  is still substantially slower than the reference backend.

## 0.2.0a1 - 2026-08-08

This is the project's first published alpha line. The `0.2` minor version marks
the addition of three tested historical-compatibility milestones beyond the
original reference-frontend prototype: global declaration mode, non-Herbrand
visibility, and seed-equality safety with value variables.

### Added

- A clean-room, location-aware compatibility frontend, typed ASP{f} IR,
  inspectable reference lowering for Clingo 5.8, model enumeration, JSON output,
  and stable ASP{f}-style model reconstruction.
- Partial `#nherb` applications with functionality but no totality rule.
- Explicit and application-style declarations, exact name/arity identity, and
  global `#nherb.` mode with a documented zero-arity signature restriction.
- `#=` assignments in facts and complete rule heads.
- Positive and singly default-negated body `#=`, `#!=`, `#<`, `#<=`, `#>`, and
  `#>=`, including application-to-application operands. Ordered comparison is
  defined-integer-only and performs no coercion.
- Direct domain-safe key variables, positive scalar seed-equality safety,
  complete body equality value variables, and independently safe inequality
  value variables.
- Historical `#hide #nherb` and `#show #nherb` presentation controls, including
  exact selectors and the documented ordinary hide-all bridge.
- A manifest-derived historical compatibility corpus, conformance corpus,
  architecture decisions, primary-source design notes, guided examples, and a
  synthetic partial-indicator portfolio demo.
- Python 3.11 and 3.12 CI with Ruff, mypy, pytest, conformance, and historical
  compatibility checks.

### Semantic safeguards

- Undefined applications remain distinct from zero, false, inequality, and
  guessed values.
- Positive inequality and ordering require defined operands; ordered comparison
  cannot fall through to generic Clingo term order.
- Default negation remains failure of positive satisfaction rather than an
  operator complement.
- Generated backend predicates cannot supply source safety, and user executable
  identifiers beginning with `__aspf_` are rejected.
- Ordinary uses of declared spellings remain ordinary Herbrand syntax outside
  supported n-atoms; visibility policy cannot affect stable models.

### Known limitations

- `_V` non-Herbrand variables are not implemented. Research concluded that the
  relational reference backend cannot preserve their grounder-inert behavior
  without value-domain grounding; a native theory/propagator backend remains a
  separate research direction.
- Arithmetic inside n-atoms and n-atoms in aggregates, choices, disjunctions,
  or conditional literals are unsupported.
- Nested application operands, ordered value variables, and assignment-head
  value variables are unsupported.
- The backend is a correctness-oriented reference translation, not a native
  solver extension and not a historical grounding-efficiency claim.
- This is experimental alpha research software and does not claim full ASP{f}
  or Clingo{f} compatibility.
