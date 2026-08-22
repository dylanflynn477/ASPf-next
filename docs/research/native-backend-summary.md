# Native backend feasibility: technical summary

## Current baseline

Published ASPf-next 0.2.0a1 and the unpublished 0.2.0a2 candidate share the same
clean-room compatibility frontend and reference-backend language boundary for modern
Clingo 5.8. They reproduce a bounded set of partial-function model semantics by lowering
n-atoms to ordinary relations with functionality and no totality rule. This path is
inspectable and useful as an executable semantic reference, but a relation variable
used to copy a value is grounded over its candidate domain.

Historical Clingo{f} n-variables such as `_v` were deliberately treated as ground
expressions during grounding and evaluated later. Translating `_v` to an ordinary
Clingo variable therefore loses the operational property it was introduced to provide.

## Prototype

The feasibility prototype translates a separate typed research IR to ground Clingo
theory metadata and registers a Python propagator. N-variable identity is encoded as a
lowercase ground term associated with a grounded rule instance. Ordinary variables are
still grounded normally. The propagator maintains explicit application/n-variable
states, evaluates definitions and comparisons, enforces functionality, and reconstructs
visible assignments from a thread-scoped model snapshot. Literal-to-seed and
application-to-rule indexes update only affected per-thread supports, and undo removes
exactly the reverted supports. One- and two-thread modes are bounded research options;
all performance measurements use one thread.

The released frontend, backend, CLI, and package API do not invoke the prototype.

## Results

Focused and generated tests cover copy/binding, definitions, explicit undefinedness,
comparisons, functionality, backtracking, ordinary-variable grounding, dependency
chains and diamonds, repeated controls, and two-thread exhaustive solving. A 144-case
matrix exhausts small comparison/undefinedness/n-variable combinations. Differential
tests compare normalized visible model sets, not private atoms.

For candidate domains 10 through 10,000, relational copy overhead grows from 10 to
10,000 grounded rules and atoms. Native copy overhead remains one grounded rule and one
theory atom. Complete normalized copy models remain equal at all five sizes. At
N=10,000 the final medians are 0.706 seconds for native first-model solve, 2.657 seconds
for exhaustive raw enumeration, and 3.308 seconds for exhaustive visible solving. The
reference medians are 0.030, 1.611, and 10.603 seconds respectively. Initialization is
0.692 seconds of the native first-model result.

The earlier visible path scanned every symbolic atom for every model. At N=10,000,
`model.symbols()` plus ordinary rendering accounted for about 2.88 seconds. Indexing
visible solver literals once and trailing true atoms reduces those two components to
about 2.8 milliseconds total. Native exhaustive-visible median falls from 6.497 to
3.308 seconds, while digest work remains measured separately. This is a real output
path improvement, not a claim that native search beats Clingo.

The typed n-loop module implements explicit literal nodes, positive-body and
literal-match edges, full simple-term keys, deterministic traversal, and source
provenance. It detects direct and ordinary-atom-mediated n-loops, ignores
default-negated edges, distinguishes `f(a)` from `f(b)`, and does not reject ordinary
ASP recursion. It is exact for the variable-free constant-head research subfragment
and conservative for ordinary-variable or dynamic-head patterns.

The propagator now retains deterministic solver-literal support sets through derived
values, n-variable definitions, comparisons, and guards. It evaluates guarded and
multi-provider rule families on relevant watched changes, installs narrow clauses, and
keeps clause and evaluation caches per solver thread. An explicit semantic generation
validates each cached positive closure. At total checks, a least fixed point can also
justify dynamic absence when every grounded provider has a proved failure. False
solver literals are evidence; don't-cares and unsupported cycles are not.

The original three-device multi-application result at N=1,000 emitted 7,482 broad
clauses containing 7,504,446 literals, with maximum width 1,003. The post-hardening run
retains exact models and the same 2,032-versus-8,012 grounding result while emitting
2,001 narrow clauses, zero broad clauses, 4,001 clause literals, and maximum width two.
Checks fall from 8,482 to 1,003 and median native solve time falls from 4.527 to 0.374
seconds across the recorded artifacts. The artifacts use different Clingo patch
versions, so deterministic work counts—not that timing ratio—are the primary evidence.
The current reference median is 0.009 seconds, so this remains a research improvement
rather than a production-performance result.

A same-environment follow-up caches the evaluation already produced during early
propagation and reuses it at total checks. At N=1,000, all 1,003 checks are cache hits,
rule-body evaluations fall from 27,009 to 17,982, and the seven-sample native median
falls from 0.374 to 0.304 seconds. Clause counts, widths, and exact model digests are
unchanged. Profiled closure evaluation remains the dominant Python callback cost, so
this does not justify production integration.

## Decision

**PARTIAL GO for continued research; NO-GO for production integration.**

An adversarial review found no narrow clause that excluded a reference model, but it
did find an unlocked broad fallback incorrectly remembered as permanent even though
Clingo may delete it. The fallback cache entry was removed. Opt-in one-thread clause
records now expose exact signed supports and origins for audit.

The experiment establishes that Python-level theory metadata can retain a grounder-inert
n-variable identity and reproduce a meaningful semantic subset. It does not establish
the full historical boundary. Wider non-ground n-loop analysis is conservative,
cross-type ordered semantics are unproved, two-thread evidence is bounded rather than
production-grade, dynamic undefinedness remains incomplete for unassigned/cyclic
provider paths, and no historical-source adapter connects the prototype to the
released IR.

## Remaining questions

1. How should closure and provider-failure proofs be maintained incrementally without
   repeating rule-body evaluation?
2. Can n-loop analysis run on grounded typed metadata and still report source paths?
3. Can Python evaluation, callback, initialization, and raw enumeration costs be
   reduced materially?
4. Does two-thread state remain sound under larger conflicting stress cases?
5. Do remaining reason-tracking and callback costs justify a native Clingo extension?
6. What production IR identity should distinguish the same textual n-variable across
   grounded rule instances?

The detailed [research report](native-backend-feasibility.md) and
[benchmark report](../benchmarks/native-vs-reference.md) contain the contract, raw-data
links, environment, limitations, and scientific-integrity review.
