# Native backend feasibility contract

Status: pre-implementation research contract  
Scope: Clingo 5.8 theory atoms and the Python propagator API  
Released backend: unchanged

## Problem statement

The current reference backend can reproduce many ASP{f} answer-set semantics by
lowering to ordinary Clingo relations, but historical non-Herbrand variables were
intentionally grounder-inert. Translating them to ordinary Clingo variables defeats
that property.

This investigation asks whether a clean-room Python backend can keep a rule-local
non-Herbrand variable out of ordinary grounding, evaluate it during solving, preserve
the observable ASP{f} semantics, and improve the structural grounding growth of the
copy benchmark described below. A negative result is useful: the experiment must not
recover apparent success by silently returning to a relational grounding.

The research prototype is isolated under `research/`. It does not extend the released
language, alter the reference lowering, or add a user-facing backend switch.

## Primary-source basis

Balduccini's ASP{f} account treats underscore-prefixed non-Herbrand variables as
ground expressions unaffected by grounding, gives the defining-equality and
n-stratification restrictions, and describes an explicit undefined value and the
n-loop-free scope of the soundness/completeness result [Balduccini 2013, pp. 5-8].
This project uses those published semantics, not historical implementation source.

The Clingo 5.8 API exposes grounded theory atoms and maps their program literals to
solver literals during propagator initialization. Propagators can watch solver
literals, inspect thread-local assignments, add clauses, and receive undo callbacks.
Theory-atom inspection is confined to initialization; newly created volatile solver
literals are not symbolic atoms. These lifecycle facts define the experimental
boundary [Clingo theory-atom API], [Clingo propagator API], [Clingo statistics API].

[Balduccini 2013, pp. 5-8]: https://mbal.asklab.net/papers/bal13.pdf
[Clingo theory-atom API]: https://potassco.org/clingo/python-api/5.8/clingo/theory_atoms.html
[Clingo propagator API]: https://potassco.org/clingo/python-api/5.8/clingo/propagator.html
[Clingo statistics API]: https://potassco.org/clingo/python-api/5.8/clingo/statistics.html

## Meaning of native-backend success

Success is not merely parsing `_v`, finding the same value after solving, or hiding a
relational join. A GO requires every essential semantic and operational gate below.
The prototype must use a rule-local identity for each n-variable occurrence after
ordinary-variable grounding, and Clingo must never see that identity as an ordinary
source variable.

### Semantic gates

The prototype must demonstrate, with normalized visible-model assertions:

1. partial application values and explicit solver-side undefinedness;
2. functionality of each non-Herbrand application;
3. rule-local n-variable identity and positive defining equalities;
4. one definition, agreeing definitions, conflicting definitions, and an undefined
   defining expression;
5. dependent equality, inequality, and ordered comparisons where the experimental
   subset claims them;
6. default negation as failure of the corresponding positive comparison, including
   undefined operands;
7. correct restoration across backtracking and exhaustive multiple-model enumeration;
8. ordinary-variable grounding followed by independent n-variable evaluation for each
   grounded rule instance;
9. n-stratification rejection for self-cycles, mutual cycles, and missing positive
   definitions;
10. rejection of forbidden n-variable positions; and
11. explicit detection or conservative rejection of the program-level n-loop cases
    outside the published sound/complete subset.

For every case expressible by both encodings, the acceptance threshold is exact set
equality of normalized visible models, including satisfiability and exhaustive model
count. Private atoms are excluded from both sides before comparison.

### Operational gates

The benchmark family contains one selected source value and a copy rule conceptually
equivalent to:

```asp
h(x) #= _v :- f(x) #= _v.
```

It is compared with the relational approximation:

```asp
__aspf_value(h(x),V) :- __aspf_value(f(x),V).
```

The tested candidate-domain sizes are 10, 100, 1,000, 5,000, and 10,000 unless a run
is stopped and documented for resource safety. The reference and native cases must
represent the same set of visible copy models.

A GO requires all of the following:

- the n-variable is encoded as ground metadata in theory atoms, never as a Clingo
  variable;
- reference copy overhead grows linearly with candidate-domain size;
- native copy overhead, measured as grounded rules and atoms above its no-copy
  baseline, remains constant across the tested sizes;
- unrelated constants added to the Herbrand universe neither become candidate values
  nor change the native visible models; and
- native and reference normalized visible models are exactly equal at every tested
  semantic size.

Grounded-rule/atom/body deltas are the decision metrics. Timing is informational. One
warm-up and seven measured runs are used; reports give medians and interquartile ranges
and make no speed claim from tiny or noisy samples. Memory is reported only if it can
be measured portably without a new dependency.

### Engineering gates

The prototype must:

- use typed dataclasses, enums, and explicit interfaces for program and solver state;
- keep mutable state on a backend/propagator instance, never at module scope;
- separate immutable program metadata from per-solving-thread assignment state;
- either prove multi-thread behavior or explicitly enforce a single solving thread;
- handle undo without retaining values from abandoned branches;
- produce deterministic normalized output and structural metrics;
- remain outside `src/aspf_next` unless every GO gate passes and integration receives
  separate review;
- reserve private implementation data from user-visible output; and
- include semantic, differential, lifecycle, and deterministic scaling tests.

The experimental implementation must not parse raw strings after construction of its
typed research IR. Any source adapter must validate into that IR before solving.

## Decision rule

- **GO**: every essential semantic, operational, and engineering gate passes, including
  the claimed n-loop scope.
- **PARTIAL GO**: the architecture proves grounder-inert behavior and a coherent,
  tested semantic subset, but at least one essential historical property or production
  engineering requirement remains unproved.
- **NO-GO**: an essential property cannot be represented faithfully through the Python
  API, the grounding-growth gate fails, or the result depends on disguising an ordinary
  relational grounding.

Missing evidence is a failed gate, not an assumed success. PARTIAL GO and NO-GO keep
all code under `research/`, expose no CLI option, and make no compatibility claim for
the released frontend.

## Measurement record

The benchmark runner will record its input family, repeat count, random-free generated
source, Python and Clingo versions, platform and architecture, CPU description when
available, date, repository commit, raw observations, and aggregate metrics in JSON.
Observer callbacks count grounded rules, atoms, and bodies; Clingo statistics provide
ground/solve/total timing where available. Process memory is omitted if the standard
library cannot obtain a comparable portable measure, and that omission will be stated
in the result report.

## Research sequence

1. Freeze this contract before prototype implementation.
2. Measure the reference relation family.
3. Implement the smallest positive copy prototype.
4. Attempt n-stratification, multiple definitions, backtracking, functionality,
   undefinedness/default negation, ordinary-variable separation, forbidden positions,
   and n-loop handling in that order.
5. Stop production expansion at the first architectural blocker; retain a minimal
   reproducer and classify the result by the rule above.
6. Run structural scaling and semantic differential tests, then publish the evidence
   and scientific-integrity review.
