# Roadmap

This roadmap distinguishes shipped behavior from possible research directions.
Items beyond the implemented surface are proposals, not commitments or
compatibility claims.

## Milestone 0.1 — restricted reference frontend

Implemented:

- location-aware compatibility scanning and validation;
- `#nherb f/n.` declarations;
- ground `#=` assignments in facts and complete rule heads;
- positive ground `#=` comparisons in rule bodies;
- integer, symbolic constant, and string values;
- inspectable reference lowering to ordinary Clingo 5.8;
- partiality and functionality without a totality rule;
- model enumeration, normalized human output, and JSON output; and
- explicit diagnostics for unsupported ASP{f}-shaped syntax.

See the [supported-language document](supported-language.md) for the normative
boundary.

## Milestone 0.2 conformance foundation

Implemented without changing the milestone 0.1 accepted language:

- map every milestone 0.1 construct to primary sources, implementation, tests,
  and known deviations;
- execute a machine-readable conformance corpus across source layout and
  multi-file programs; and
- record the architectural decisions that protect the semantic boundary.

## Implemented compatibility increments

Positive ground `#!=` is implemented on the development branch only as a
complete positive body literal. Both operands must be defined, so an undefined
left application makes the comparison false. The reference backend performs an
explicit value lookup followed by ordinary inequality; it does not treat
inequality as the absence of equality. No release number has been assigned to
this increment.

Positive fully ground `#<`, `#<=`, `#>`, and `#>=` body literals are also
implemented on the development branch for integer values and integer right
operands only. Undefined and non-integer application values make the comparison
false. No coercion, arithmetic, or variable support is included, and no release
number has been assigned.

## Next compatibility candidates

Arithmetic expressions, variables inside n-atoms, application-to-application
comparisons, and every broader n-atom context remain deferred. Each candidate
requires its own primary-source review, explicit undefinedness rule, typed IR,
conservative diagnostics, and focused conformance cases.

## Later research

Longer-term topics may include:

- additional comparisons and arithmetic;
- non-Herbrand variables;
- aggregates containing n-atoms;
- an alternative backend using Clingo theory atoms or a custom propagator;
- equivalence and grounding-size studies comparing backends; and
- an explainable portfolio-risk demonstration built only after the language
  semantics it needs are specified and tested.

None of these later language capabilities is implemented by the
ordered-comparison increment. A native backend would be a separate research
milestone, not a silent replacement for the reference translation.
