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
exactly the reverted supports. It requires one solver thread.

The released frontend, backend, CLI, and package API do not invoke the prototype.

## Results

The basic copy, multiple definitions, explicit undefinedness, functionality,
default-negated equality/inequality, multiple models, backtracking, ordinary-variable
grounding, and rule-local n-variable separation pass focused tests. A differential
harness reports exact visible-model equality with relational encodings for shared
cases. Rule-local self/mutual n-stratification cycles and missing definitions receive
location-aware rejection.

For candidate domains 10 through 10,000, relational copy overhead grows from 10 to
10,000 grounded rules and atoms. Native copy overhead remains one grounded rule and one
theory atom. Complete normalized copy model sets are equal at all five sizes.

Profiling confirmed that the initial solver rescanned every candidate seed at every
model: N=1,000 caused one million seed probes and 1,002,000 calls to
`Assignment.value`. Incremental watched-literal state removes all check-time seed
probes. At N=1,000, median exhaustive native solve time falls from 1.193 seconds to
0.156 seconds (7.67×), with 1,000 seed activations, 1,000 matching undo removals, and
1,000 rule evaluations. The full seven-sample experiment now completes at N=5,000 and
N=10,000; the latter has a 4.189-second native median and exact model equality.

The native implementation is still slower than the relation case (0.0076 seconds at
N=1,000 and 1.301 seconds at N=10,000). At N=10,000, eager reconstruction of all
visible models takes a 2.004-second median and is the largest measured component.
This is a solve-scaling improvement, not an end-to-end speed or production claim.

## Decision

**PARTIAL GO for continued research; NO-GO for production integration.**

The experiment establishes that Python-level theory metadata can retain a grounder-inert
n-variable identity and reproduce a meaningful n-loop-free-style semantic subset. It
does not establish the full historical boundary. Exact published program-level n-loop
detection is missing, cross-type ordered semantics are unproved, only one solving thread
is supported, clauses are broad model filters rather than strong explanations, and no
historical-source adapter connects the prototype to the released IR.

## Remaining questions

1. Can a streaming or digest-only research solve path separate search cost from eager
   materialization of every visible model without weakening semantic comparisons?
2. What minimal clauses explain application functionality and comparison guards?
3. How should the exact positive dependency/n-loop definition be represented after
   ordinary grounding?
4. Can multi-thread state be proven safe without serializing callbacks?
5. Do remaining theory-value decoding, model-symbol extraction, and Python callback
   costs justify a native Clingo theory propagator on representative workloads?
6. What production IR identity should distinguish the same textual n-variable across
   grounded rule instances?

The detailed [research report](native-backend-feasibility.md) and
[benchmark report](../benchmarks/native-vs-reference.md) contain the contract, raw-data
links, environment, limitations, and scientific-integrity review.
