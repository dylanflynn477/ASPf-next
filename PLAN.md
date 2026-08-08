# Maintained project plan

This file records active project direction rather than branch-specific
implementation scratchwork. Completed release work belongs in `CHANGELOG.md`;
semantic decisions and research outcomes belong in `docs/decisions/` and
`docs/design/`.

## Current objective

Maintain ASPf-next as an experimental, compatibility-first clean-room frontend
for a documented subset of ASP{f} on Clingo 5.8. Every accepted construct must
have typed IR, explicit semantics, location-aware diagnostics, executable
coverage, and accurate compatibility classification.

## Near-term priorities

1. Keep the reference backend, CLI, examples, compatibility manifests, and
   public documentation synchronized.
2. Expand adversarial tests around partiality, source safety, declaration
   scope, visibility, and private-namespace isolation without expanding the
   language by accident.
3. Investigate a theory-atom/custom-propagator backend for grounder-inert
   non-Herbrand variables. This is research, not a committed release feature.
4. Consider each remaining historical construct separately, beginning with a
   primary-source semantic contract and a GO/NO-GO review.

## Explicitly deferred language work

- arithmetic expressions inside n-atoms;
- n-atoms inside aggregates, choices, disjunctions, or conditional literals;
- `_v` non-Herbrand variables on the relational reference backend;
- broader variable positions and inferred numeric domains; and
- any claim of historical grounding efficiency or full Clingo{f}
  compatibility.

## Release discipline

Before any release or compatibility increment:

- run Ruff formatting and lint checks, mypy, the complete pytest suite, the
  conformance suite, and the historical compatibility suite;
- regenerate the compatibility report from its manifest;
- validate a clean install on supported Python versions;
- verify normal human and JSON output never exposes private predicates; and
- update the changelog, supported-language specification, compatibility matrix,
  examples, and release notes together.

## Invariants

- Undefined is not zero, false, unequal, or an invented value.
- Functionality never implies totality.
- Generated backend literals cannot legalize source syntax that is unsafe.
- Visibility changes presentation only, never solver semantics.
- User executable identifiers beginning with `__aspf_` remain reserved.
- Unsupported or ambiguous syntax is rejected with a source location.
- Clingo C/C++ sources and historical Clingo{f} implementation sources remain
  outside the project.
