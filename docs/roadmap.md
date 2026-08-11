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

## Native-backend feasibility result

The bounded theory-atom/Python-propagator study is complete with a **PARTIAL GO for
continued research and NO-GO for production integration**. The prototype keeps `_v`
out of ordinary grounding, preserves the tested copy/undefinedness/backtracking models,
and holds copy-rule grounding overhead to one rule/theory atom through 10,000 candidate
values. Its total-assignment state reconstruction scales poorly during exhaustive
solving on rule-heavy workloads, non-ground n-loop detection remains conservative,
and two-thread support has only bounded feasibility evidence.

The code remains under `research/`; the released syntax, reference backend, and CLI are
unchanged. The [feasibility report](research/native-backend-feasibility.md) and
[benchmark report](benchmarks/native-vs-reference.md) record the preregistered gates,
raw evidence, and limitations.

The next native research step, if pursued, is incremental watched support with precise
undo/explanation clauses plus grounded exact n-loop analysis. Production IR or CLI
integration should not begin until those gates pass.

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
