# Native backend feasibility contract

- Status: completed feasibility study — **PARTIAL GO**
- Scope: Clingo 5.8 theory atoms and the Python propagator API
- Released backend: unchanged

The contract below was committed before implementation. The evidence and decision
following it record the outcome without weakening those gates.

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

## Experimental architecture

The prototype lives in `research/native_backend/` and has no import or execution path
from `src/aspf_next`. It accepts a separate typed research IR, validates it, and emits
internal ground theory metadata. For example, `_v` is encoded as `nvar(v)`, a lowercase
ground theory term. It is never emitted as `_v`, `V`, or another ordinary Clingo
variable.

Ordinary variables remain ordinary variables in the generated theory source and must
be bound by positive ordinary body atoms. Clingo grounds those variables first. Each
grounded theory-rule instance contains its own `meta(rule_id,...)` key, so the same
textual n-variable name in different ordinary groundings has independent state.

```text
typed research IR
  -> safety, n-stratification, and cycle screens
  -> ground theory metadata + ordinary ASP conditions
  -> Clingo grounding (ordinary variables only)
  -> single-thread Python propagator
  -> thread-scoped value snapshot
  -> normalized ordinary atoms + ASP{f} assignments
```

`Propagator.init` is the only theory-inspection point. It maps theory program literals
to solver literals, installs watches, requires one solver thread, and selects total
assignment checks plus undo callbacks. At each total assignment, the prototype:

1. reads active seed and rule literals;
2. reconstructs application values without an ordinary `undefined` constant;
3. evaluates n-variable definitions in dependency order;
4. evaluates positive/default-negated comparisons;
5. derives solver-side assignment heads to a fixed point;
6. rejects functionality conflicts or a mismatched ordinary-head guard with a clause;
7. records only a valid immutable snapshot for model reconstruction; and
8. deletes that thread's snapshot on undo.

Recomputation at total assignments is deliberately simple and correctness-oriented.
It avoids stale incremental state, but it is not an efficient production propagator.
Dynamic application values are not Clingo symbolic atoms: the public API can create
volatile solver literals during solving, but it cannot add a new grounded symbolic
atom such as `h(x)=5` after grounding. Consequently, every downstream native n-atom
must be mediated by the propagator and visible assignments require custom rendering.

## Semantic results

Twenty-six focused research tests exercise the prototype and differential harness.
Every implemented semantic case passes:

| Property | Result | Evidence boundary |
| --- | --- | --- |
| smallest `f`-to-`h` copy | pass | `_v` absent from emitted ordinary-variable syntax |
| integer, symbol, and string values | pass | typed round trip; negative integer included |
| partial source / undefined n-variable | pass | no target assignment; explicit internal undefined state |
| defined zero | pass | distinguished from undefined |
| application functionality | pass | conflicting active values make the model impossible |
| one / agreeing definitions | pass | one derived value |
| conflicting definitions | pass | n-variable becomes undefined; no target value |
| undefined defining expression | pass | n-variable becomes undefined; no target value |
| multi-level definitions | pass | dependency-ordered evaluation |
| self/mutual n-stratification cycles | pass (rejected) | location-aware diagnostics |
| missing positive definition | pass (rejected) | location-aware diagnostic |
| equality and inequality | pass | positive and differential cases |
| ordered comparisons | partial | all integer operators tested; broader historical ordering not claimed |
| default negation with undefined operands | pass | both `not (=)` and `not (!=)` are true |
| multiple backtracking models | pass | no value crosses branches; undo observed |
| ordinary variables plus n-variables | pass | distinct ground theory instance per ordinary binding |
| forbidden n-variable arguments | pass (rejected) | typed boundary and location-aware diagnostic |
| repeated solve calls / independent controls | pass | deterministic model sets; no shared mutable state |
| private output | pass | no theory/private identifier in normalized models |

The reusable differential harness compares normalized visible model sets, never raw
private atoms. It covers ground assignments, functionality/unsatisfiability, equality,
inequality, integer ordering, partiality, multiple models, default negation, domain-safe
ordinary variables, and copy rules. Native and relational results agree for all shared
cases.

## N-stratification and program n-loops

Rule-local n-stratification is represented by a typed graph from each n-variable to the
n-variables in its positive defining expressions. Missing definitions, self-cycles,
and mutual cycles are rejected before Clingo sees the program. Multiple definitions of
one variable are retained rather than collapsed into ordinary unification.

The program-level screen is narrower than the published n-loop definition. It rejects
cycles in function-symbol dependencies between assignment heads and positive
application reads, including direct and mutual cycles. It can over-reject distinct
ground keys that share a function symbol, and it does not construct the complete
ordinary/n-atom positive dependency paths described by B13. Therefore it is **not
proved equivalent to historical n-loop detection**, and accepted programs are not
advertised as the full historical n-loop-free class. This failed GO gate is one reason
for the PARTIAL GO decision.

## Grounding and performance results

The reproducible raw data is in:

- `benchmarks/results/structural-scaling.json` — seven grounding-only measurements
  after one warm-up at all five sizes;
- `benchmarks/results/native-vs-reference.json` — seven exhaustive solve measurements
  after one warm-up at sizes 10, 100, and 1,000; and
- `benchmarks/results/large-model-equivalence.json` — one untimed exhaustive visible
  model comparison at sizes 5,000 and 10,000.

Observer callback counts establish the structural result:

| Candidate values | Reference copy rule delta | Reference symbolic-atom delta | Native copy rule delta | Native theory-atom delta | Visible models equal |
| ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 10 | 10 | 1 | 1 | yes |
| 100 | 100 | 100 | 1 | 1 | yes |
| 1,000 | 1,000 | 1,000 | 1 | 1 | yes |
| 5,000 | 5,000 | 5,000 | 1 | 1 | yes |
| 10,000 | 10,000 | 10,000 | 1 | 1 | yes |

Thus the copy overhead is constant in the experimental representation and linear in
the relational representation. The native baseline still contains one theory seed
atom per candidate assignment because those are the actual alternative source values;
the claim concerns the additional copy rule, not the whole program. Unrelated ordinary
constants neither become assignment values nor change the copy model set.

Median timing in milliseconds (seven samples; IQRs are in the benchmark JSON):

| Values | Reference ground | Native ground | Reference solve | Native solve |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 0.145 | 0.223 | 0.066 | 0.859 |
| 100 | 0.517 | 0.703 | 0.445 | 13.537 |
| 1,000 | 4.503 | 6.170 | 7.322 | 1,193.182 |

These measurements do **not** show a speedup. They show improved copy-rule grounding
growth together with poor solver scaling. The prototype scans every native seed
literal at every total assignment, yielding approximately candidate-literals times
enumerated-models work in this family. A preregistered repeated run through 10,000 was
stopped after more than four minutes without producing a result file; a second repeated
attempt through 5,000 was also stopped after more than three minutes. No partial timing
from either aborted run is reported. Grounding-only repeats still covered 10,000, and a
separate untimed exhaustive comparison verified all 5,000 and 10,000 visible models;
the latter command took about 140 seconds for both sizes together.

Peak process memory was not recorded because the Python standard library has no
portable, comparable peak-process measure on all supported platforms. No extra
platform-specific dependency was added for this study.

## Environment

The committed measurements record:

- benchmark date (UTC): 2026-08-11;
- benchmark input commit: `3d04ee1ddc717428800b11a79f3888e0c2311601`;
- Python: 3.12.13;
- Clingo: 5.8.1;
- platform: Windows 11 (`10.0.26200`, AMD64);
- CPU: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel; and
- logical CPU count: 12.

All solver runs explicitly use one thread. Timings describe this machine and are
informational; the deterministic rule/atom deltas are the primary evidence.

## GO decision

**PARTIAL GO for further research; NO-GO for production integration.**

The experiment proves the central feasibility proposition: theory metadata plus a
Python propagator can keep `_v` out of ordinary grounding, bind basic solver-time
values, preserve explicit undefinedness, restore state across backtracking, and keep
copy-rule grounding overhead constant for the measured family. Exact visible models
match the relation reference through 10,000 candidate values.

It does not satisfy every GO gate:

1. the full historical source frontend is not connected to this separate research IR;
2. exact historical program-level n-loop detection is not implemented or proved;
3. only single-thread solving is supported;
4. cross-type historical ordering semantics are not established;
5. total-assignment model filtering uses broad clauses rather than useful propagation
   explanations; and
6. solver performance is impractical for large exhaustive candidate families.

Accordingly there is no CLI flag, production import, version change, release, or claim
that ASPf-next now supports historical n-variables. The released reference backend and
language contract are unchanged.

## Exact next engineering questions

Before reconsidering integration:

1. replace total-state rescans with incremental per-thread application support sets,
   watched-literal deltas, and verified undo trails;
2. derive minimal explanation clauses for guard and functionality propagation;
3. implement and test the published positive dependency/n-loop criterion, including
   ordinary predicate paths;
4. prove multi-thread isolation or retain an explicit documented one-thread mode;
5. define how a production typed frontend represents rule-local n-variable identities
   after ordinary grounding; and
6. repeat differential and scaling studies without weakening the current contract.

A C++ extension is not yet proved necessary. If Python callback overhead or the lack of
symbolic solver-time value atoms prevents efficient incremental propagation, the next
alternative is a native Clingo theory propagator with a dedicated model-value channel,
not an ordinary relational fallback disguised as native support.

## Scientific-integrity review

1. **Did the benchmark compare equivalent semantics?** Yes. Both variants choose
   exactly one `f(x)` value and expose the same copied `h(x)` value; exhaustive
   normalized model sets were compared.
2. **Does it isolate grounding behavior?** Yes. Each copy variant is compared with its
   own no-copy baseline, and the structural runner does not solve.
3. **Are timing claims statistically reasonable?** Yes. Reported timing uses one
   warm-up, seven samples, medians, and recorded IQRs; interpretation is limited to the
   measured environment.
4. **Is any speed claim based on one tiny run?** No speed claim is made. The one-shot
   large run is used only for exact model equality and is explicitly untimed evidence.
5. **Did unrelated constants affect results?** No. Focused tests add unrelated symbols
   and observe no new assignment candidate or changed copy value.
6. **Does native `_V` stay out of ordinary grounding?** Yes. Generated source contains
   lowercase ground `nvar(v)` metadata and never an ordinary `_v`/`V` placeholder for
   the n-variable.
7. **Is model equality verified?** Yes. Complete normalized sets and matching SHA-256
   digests are recorded at every requested size through 10,000.
8. **Does undefinedness behave identically where expected?** Yes for the shared tested
   cases, including positive comparison failure and both default-negated operators.
9. **Does backtracking restore state?** Yes. Alternative models have isolated copied
   values, undo callbacks occur, snapshots are deleted, and repeated controls agree.
10. **Are limitations disclosed?** Yes: research-only typed input, incomplete n-loop
    coverage, single-thread restriction, broad clauses, unproved cross-type order, and
    poor solve scaling are all explicit.
