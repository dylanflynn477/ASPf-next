# Project Lazarus native-solver increment

Status: **implemented and tested in the research backend; not production-ready**.

This note records the first Project Lazarus implementation increment. It changes no
released syntax, keeps the reference backend and CLI unchanged, and does not expose
historical `_v` syntax. The implementation is an independent clean-room extension of
the existing Clingo 5.8 Python propagator experiment.

## Architectural gap analysis

| Area | Evidence-backed state | Remaining blocker |
| --- | --- | --- |
| SEMANTIC | Functionality, partiality, defined values, comparisons, rule-local typed n-variables, and the documented default-negation fragment have differential coverage. | Dynamic absence is not positive evidence when a provider is unassigned or cyclic; wider historical semantics remain unproved. |
| GROUNDING | Typed theory metadata keeps the measured copy rule at one ground rule and one theory atom through 10,000 candidates. | No production frontend-to-native compiler exists, and grounded n-loop metadata does not retain source provenance. |
| PROPAGATION | Watched seed/rule changes now invalidate a dependency-indexed forward closure. Multiple agreeing providers and retractions are represented separately. | Cyclic application dependencies deliberately use full recomputation; absence proofs are cached but not incrementally maintained per provider. |
| PERFORMANCE | The new path removes about one third of rule-body evaluations on the observation workload. | Python bookkeeping offsets the saved work at 1,000 models in the controlled profile; the reference remains faster. |
| FRONTEND / IR | The research IR has an explicit `NVariable` distinct from ordinary variables. | Production IR and parser still reject `_v`; rule-local identity and grounded-instance mapping need a typed adapter. |
| INTEGRATION | Full closure remains an independent in-process oracle and normalized native/reference models are compared exhaustively. | There is no user-facing native backend switch and no safe automatic backend selection. |
| CONCURRENCY | Every mutable cache and dirty set is thread-local; one- and two-thread adversarial tests agree. | Evidence is bounded to two threads and finite generated programs. |
| TESTING | Adversarial tests cover alternative supports, diamonds, conflicts, undefinedness, comparisons, ordering changes, repeat solves, undo, and two threads. | Bounded testing is not a proof for arbitrary programs or Clingo callback schedules. |
| DOCUMENTATION | Work counters, raw measurements, limitations, and exact fallback rules are recorded. | A future frontend milestone must update the normative language documents only after it is executable. |

The critical path is grounded typed n-loop analysis with source mapping, then a
production-IR adapter for a deliberately small `_v` fragment, followed by a new
semantic and performance review. Parser exposure before those gates would turn a
research representation into an unsupported language claim.

## Incremental closure invariant

Each solving thread owns:

- current true solver literals and seed supports;
- the exact semantic generation;
- dirty application keys and dirty grounded rules;
- the last complete application table and per-rule evaluation; and
- one optional dynamic-undefinedness proof cache.

The cached closure also retains each rule's derived output separately. This is
necessary because an aggregate value table cannot explain which derivation must be
retracted. On a watched change, the evaluator computes the forward closure from dirty
applications and rules, removes only outputs in that closure, restores unaffected
rule outputs, and reevaluates affected active rules in dependency order. A source
change therefore reaches every dependent application, comparison, n-variable state,
and guard while independent rule families remain reusable.

Dependency indexing is used only when the grounded application dependency graph is
acyclic. A cycle is not approximated: the implementation falls back to the retained
full-closure evaluator. This is independent of the source-level historical n-loop
screen and is an implementation-safety boundary, not a compatibility classification.

The optional `verify_incremental` research mode recomputes the complete closure after
every incremental evaluation and compares the full typed state, including supports,
rule satisfaction, n-variable states, explanation gaps, and derived outputs. It raises
immediately on any difference. Oracle work is counted separately and is disabled by
default.

## Undefinedness cache invariant

Absence remains a proved condition, never a missing dictionary entry. When a narrow
absence explanation is required, the propagator records the exact tuple of provider
literals that Clingo currently reports false. The cache key is:

```text
(thread-local semantic generation, exact false-provider tuple)
```

An unassigned provider is absent from that tuple and therefore cannot justify
undefinedness. Computing the signature scans providers only when dynamic absence is
needed. An attempted design that watched every negative provider literal was rejected
because it increased a 40-choice scaling case from 40 to 552 propagated literal
events. The retained design avoids that callback amplification and still makes cache
validity explicit.

## Correctness evidence

The adversarial suite runs dependency-indexed evaluation with full-oracle checking
over:

- two independent paths deriving the same value;
- path removal and restoration under undo;
- defined -> undefined -> conflict -> defined transitions;
- derivation diamonds and multiple n-variables;
- positive and default-negated comparisons;
- rule and seed reorderings;
- repeated solves and one/two solver threads; and
- complete normalized-model comparison with independent relational encodings.

No learned-clause change was required by this increment. Existing clause audits remain
the authority for signed support origins. The new evaluator reuses those explanations
only when their rule and application dependencies are outside the invalidated closure.

## Measured result

Commit `28c0697` was measured on the same Windows/Intel host with Python 3.12.14 and
Clingo 5.8.3. The same revision runs both evaluators, with one warm-up and three
measured samples:

| Models | Full rule evaluations | Indexed rule evaluations | Reduction | Full solve median | Indexed solve median |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 162 | 111 | 31.5% | 8.072 ms | 7.597 ms |
| 100 | 1,782 | 1,191 | 33.2% | 67.629 ms | 58.953 ms |
| 1,000 | 17,982 | 11,991 | 33.3% | 837.653 ms | 1,245.958 ms |

All complete visible model sets and SHA-256 digests match. A separate seven-sample
N=1,000 profile reports 1,240.347 ms for full closure and 1,326.326 ms for indexed
evaluation. The deterministic semantic-work reduction is real; a general solve-time
improvement is not. Allocation/copying in Python remains a significant cost.

The dynamic-undefinedness workload at 10, 50, and 100 providers performs one proof
analysis and one exact cache reuse per run. It probes 2N provider statuses for those
two requests and preserves zero broad clauses and exact relational/native model sets.

Raw data:

- [`lazarus-full-vs-incremental.json`](../../benchmarks/results/lazarus-full-vs-incremental.json)
- [`lazarus-full-vs-incremental-1000-profile.json`](../../benchmarks/results/lazarus-full-vs-incremental-1000-profile.json)
- [`lazarus-incremental-after.json`](../../benchmarks/results/lazarus-incremental-after.json)
- [`lazarus-undefinedness-cache.json`](../../benchmarks/results/lazarus-undefinedness-cache.json)

## Readiness decision

**PARTIAL GO for further native research; NO-GO for production integration.**

Implemented and tested: dependency-indexed acyclic closure, sound retraction through
rebuild of the affected closure, full-oracle verification, and exact absence-cache
keys.

Implemented but experimental: the typed native IR, Python propagator, bounded
two-thread mode, and native performance counters.

Researched but not implemented: grounded typed n-loop analysis with source provenance,
cost-aware incremental state storage, and a production frontend adapter.

Unsupported: real source `_v` syntax, native CLI selection, arithmetic in native
n-atoms, aggregate/choice n-atoms, and programs rejected by the existing n-loop or
n-stratification screens.

Blocked by architecture: safely exposing `_v` requires grounded rule-instance identity
and exact-enough n-loop validation that can still report a source location. The current
pre-ground conservative analyzer and post-ground propagator metadata do not yet share
that mapping.
