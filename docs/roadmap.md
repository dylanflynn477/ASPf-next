# Roadmap

This roadmap distinguishes shipped behavior from possible research directions.
Items beyond milestone 0.1 are proposals, not commitments or compatibility
claims.

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

## Potential milestone 0.2

Candidate work, subject to primary-source semantic review:

- investigate `#!=` semantics and add it only with specification-backed tests;
- expand conformance tests across source layout and multi-file programs;
- strengthen traceability from compatibility decisions to historical ASP{f}
  publications; and
- refine diagnostics and packaging based on early-user feedback.

## Later research

Longer-term topics may include:

- additional comparisons and arithmetic;
- non-Herbrand variables;
- aggregates containing n-atoms;
- an alternative backend using Clingo theory atoms or a custom propagator;
- equivalence and grounding-size studies comparing backends; and
- an explainable portfolio-risk demonstration built only after the language
  semantics it needs are specified and tested.

None of these capabilities is implemented in milestone 0.1. A native backend
would be a separate research milestone, not a silent replacement for the
reference translation.
