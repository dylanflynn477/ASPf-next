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
visible assignments from a thread-scoped model snapshot. It requires one solver thread
and removes snapshots on undo.

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

The current solver algorithm is not performant. At 1,000 candidates, median exhaustive
solve time is approximately 1.19 seconds for native versus 0.0073 seconds for the
relation case on the recorded machine. The native implementation rescans all candidate
seed literals at every total assignment. The favorable grounding result therefore is
not an end-to-end speed result.

## Decision

**PARTIAL GO for continued research; NO-GO for production integration.**

The experiment establishes that Python-level theory metadata can retain a grounder-inert
n-variable identity and reproduce a meaningful n-loop-free-style semantic subset. It
does not establish the full historical boundary. Exact published program-level n-loop
detection is missing, cross-type ordered semantics are unproved, only one solving thread
is supported, clauses are broad model filters rather than strong explanations, and no
historical-source adapter connects the prototype to the released IR.

## Remaining questions

1. Can incremental watched support sets and undo trails remove total-state rescanning
   while retaining deterministic semantics?
2. What minimal clauses explain application functionality and comparison guards?
3. How should the exact positive dependency/n-loop definition be represented after
   ordinary grounding?
4. Can multi-thread state be proven safe without serializing callbacks?
5. Does Python callback overhead remain acceptable after an incremental design, or is a
   native Clingo theory propagator required?
6. What production IR identity should distinguish the same textual n-variable across
   grounded rule instances?

The detailed [research report](native-backend-feasibility.md) and
[benchmark report](../benchmarks/native-vs-reference.md) contain the contract, raw-data
links, environment, limitations, and scientific-integrity review.
