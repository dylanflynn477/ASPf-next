# Roadmap

This roadmap separates implemented behavior from research candidates. Nothing
in the candidate sections is a compatibility promise.

## 0.2.0a1 release baseline

Implemented and tested:

- context-aware scanning, typed IR, reference lowering to Clingo 5.8, solving,
  model enumeration, and normalized human/JSON output;
- partial non-Herbrand assignments with functionality and no totality rule;
- explicit/application declarations, exact name/arity identity, and global
  `#nherb.` with a zero-arity signature restriction;
- `#=`, `#!=`, and integer-only `#<`, `#<=`, `#>`, `#>=` body comparisons;
- application operands and one-level default negation with definedness-aware
  semantics;
- ordinary direct-key variables with domain-safe ordinary atoms or positive
  scalar seed equality, plus restricted body value variables;
- historical non-Herbrand visibility controls as presentation policy; and
- executable conformance and historical compatibility manifests.

The exact current contract is the [supported-language specification](supported-language.md).
The manifest-derived historical report records 35 compatible cases, 7
compatible-with-restriction cases, 2 matching rejections of historically
invalid inputs, 4 unsupported cases, 4 intentionally deferred cases, and no
unresolved cases.

## Next technical milestone: native-backend feasibility

The recommended next milestone is a bounded prototype using Clingo theory atoms
and a custom Python propagator to test whether historical grounder-inert
non-Herbrand variables can be represented faithfully. Its GO criteria must
include semantic equivalence, no ordinary value-domain grounding, stable
undefinedness, and reasonable grounding growth. The existing
[n-variable analysis](design/non-herbrand-variables.md) explains why the
relational reference backend is a NO-GO for this feature.

This prototype must remain separate from the reference backend and cannot alter
the released syntax unless its semantics and operational behavior pass review.

## Deferred compatibility candidates

Each candidate requires primary-source research, a typed design, explicit
undefinedness rules, conservative diagnostics, and focused conformance tests:

- arithmetic expressions inside n-atoms;
- broader ordinary-variable positions and numeric-domain evidence;
- n-atoms inside aggregates;
- n-atoms inside choice, disjunctive, or conditional constructs; and
- additional historical visibility or grounding behavior not represented by
  the current corpus.

## Permanent project guardrails

- No copied historical implementation code and no Clingo C/C++ fork.
- No silent totality, coercion, invented values, or operator-complement rewrite.
- No claim of full historical compatibility or historical grounding
  efficiency from the reference translation.
- Unsupported and ambiguous ASP{f}-shaped syntax remains location-aware and
  explicit.
