# Native backend feasibility: technical summary

## Current baseline

ASPf-next 0.2.0a1 is a clean-room compatibility frontend and reference backend for
modern Clingo 5.8. It reproduces a bounded set of partial-function model semantics by
lowering n-atoms to ordinary relations with functionality and no totality rule. This
path is inspectable and useful as an executable semantic reference, but a relation
variable used to copy a value is grounded over its candidate domain.

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

Forty-three focused tests cover copy/binding, definitions, explicit undefinedness,
comparisons, functionality, backtracking, ordinary-variable grounding, dependency
chains and diamonds, repeated controls, and two-thread exhaustive solving. Differential
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

Direct seed functionality conflicts now receive clauses containing only the two
incompatible supports. Derived functionality and guard mismatches still use broad
total-assignment clauses. A three-device multi-application workload confirms both the
grounding property and this limitation: at N=1,000 it grounds 2,032 native versus 8,012
reference rules with exact models, but native solve takes 4.527 seconds versus 0.010
seconds and emits 7,482 broad clauses. Visible reconstruction is only 0.022 seconds in
that workload.

## Decision

**PARTIAL GO for continued research; NO-GO for production integration.**

The experiment establishes that Python-level theory metadata can retain a grounder-inert
n-variable identity and reproduce a meaningful semantic subset. It does not establish
the full historical boundary. Wider non-ground n-loop analysis is conservative,
cross-type ordered semantics are unproved, two-thread evidence is bounded rather than
production-grade, derived explanations remain broad, and no historical-source adapter
connects the prototype to the released IR.

## Remaining questions

1. How should a provenance DAG retain actual supports for derived values, comparison
   truth, and undefinedness?
2. Can n-loop analysis run on grounded typed metadata and still report source paths?
3. Can Python initialization and raw enumeration costs be reduced materially?
4. Does two-thread state remain sound under larger conflicting stress cases?
5. Do remaining reason-tracking and callback costs justify a native Clingo extension?
6. What production IR identity should distinguish the same textual n-variable across
   grounded rule instances?

The detailed [research report](native-backend-feasibility.md) and
[benchmark report](../benchmarks/native-vs-reference.md) contain the contract, raw-data
links, environment, limitations, and scientific-integrity review.
