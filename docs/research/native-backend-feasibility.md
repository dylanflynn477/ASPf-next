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
  -> safety, n-stratification, and typed n-loop analysis
  -> ground theory metadata + ordinary ASP conditions
  -> Clingo grounding (ordinary variables only)
  -> one- or two-thread Python propagator experiment
  -> thread-scoped value snapshot
  -> normalized ordinary atoms + ASP{f} assignments
```

`Propagator.init` is the only theory-inspection point. It maps theory program literals
to solver literals, canonicalizes repeated application/value terms within that one
initialization, constructs literal-to-seed and application-to-rule indexes, installs
positive watches for every solver thread, and selects total checks plus undo callbacks.
Mutable support maps and snapshots remain keyed by thread; decoded theory metadata and
indexes are immutable after initialization. The public research solver accepts only
one or two threads because that is the evaluated boundary. A propagation callback adds
only the seeds associated with newly true watched literals; undo removes exactly those
supports.

The prototype evaluates active rules through an application-dependency work queue and
retains deterministic positive solver-literal support sets for seeds, derived values,
n-variable definitions, comparisons, and guards. Direct and derived functionality
conflicts and explained guard mismatches receive clauses containing only their actual
supports. Guarded or multi-provider families are evaluated on relevant watched changes
so those clauses can propagate before a total check. Total checks remain the validation
and snapshot boundary; they copy the usually small active support map and use a broad
completion clause only when no justified support explanation is available. Provider
rules are ordered before consumers, and a rule is reconsidered only when an application
it reads gains a value. Total checks do not scan the grounded candidate-seed domain.

A grounded potential-application fixed point soundly proves unconditional
undefinedness where no seed or viable provider path exists. It deliberately
over-approximates potential derivations. Dynamic absence caused by inactive supports is
not treated as proof of falsehood because Clingo total checks may still contain
don't-care solver literals; those cases retain an explicit explanation gap.

Dynamic application values are not Clingo symbolic atoms: the public API can create
volatile solver literals during solving, but it cannot add a new grounded symbolic
atom such as `h(x)=5` after grounding. Consequently, every downstream native n-atom
must be mediated by the propagator and visible assignments require custom rendering.
The incremental design is still a research propagator, not a production backend.

## Semantic results

Forty-six focused research tests exercise the prototype and differential harness.
Every implemented semantic case passes:

| Property | Result | Evidence boundary |
| --- | --- | --- |
| smallest `f`-to-`h` copy | pass | `_v` absent from emitted ordinary-variable syntax |
| integer, symbol, and string values | pass | typed round trip; negative integer included |
| partial source / undefined n-variable | pass | no target assignment; explicit internal undefined state |
| defined zero | pass | distinguished from undefined |
| application functionality | pass | conflicting active values make the model impossible |
| direct functionality explanation | pass | two relevant seed supports; width at most two |
| derived functionality explanation | pass | actual transitive positive supports; unit or empty reasons tested |
| guard explanation | pass | comparison truth/failure clauses retain actual supports; width at most two in workload |
| undefinedness explanation | partial | exact static no-provider proof; dynamic absence remains unexplained |
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
| incremental support trail | pass | literal-local add/remove counts; blocked branch restored |
| reversed assignment chain | pass | provider ordering; each body evaluated once |
| dependency diamond / two n-variables | pass | exhaustive backtracking; no stale value |
| ordinary variables plus n-variables | pass | distinct ground theory instance per ordinary binding |
| forbidden n-variable arguments | pass (rejected) | typed boundary and location-aware diagnostic |
| repeated solve calls / independent controls | pass | deterministic model sets; no shared mutable state |
| two solver threads | bounded pass | 20 exhaustive models match one-thread and repeated runs |
| typed n-loop analysis | partial | exact ground constant-head subfragment; conservative wider screen |
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

The program-level analysis now constructs explicit typed literal occurrences,
positive-body edges, occurrence-matching edges, full simple-term keys, and source
provenance. It rejects direct paths and paths bridged by ordinary positive literals,
does not treat default-negated comparisons as positive edges, distinguishes `f(a)`
from `f(b)`, and does not confuse an ordinary ASP cycle with an n-loop. Deterministic
tests cover each boundary and a rule that is n-stratified but still has an n-loop.

The analysis is exact for the variable-free research subfragment with constant-valued
assignment heads. Ordinary-variable patterns and dynamic n-variable assignment heads
are checked conservatively by possible literal unification, so the wider accepted
class is not advertised as exact historical n-loop detection. The full definition,
examples, implementation contract, and primary sources are recorded in the focused
[n-loop analysis note](n-loop-analysis.md).

## Grounding and performance results

The reproducible raw data is in:

- `benchmarks/results/structural-scaling.json` — seven grounding-only measurements
  after one warm-up at all five sizes;
- `benchmarks/results/native-vs-reference.json` — seven exhaustive solve measurements
  before incremental optimization at sizes 10, 100, and 1,000;
- `benchmarks/results/native-vs-reference-incremental.json` — seven exhaustive solve
  measurements after one warm-up at all five sizes, with deterministic propagator work
  counters and separate initialization/model-reconstruction timings;
- `benchmarks/results/solve-decomposition-before-visible-index.json` and
  `solve-decomposition-after-visible-index.json` — paired output-cost profiles before
  and after removing per-model symbolic-atom scans;
- `benchmarks/results/solve-decomposition-final.json` — final first-model, fixed-ten,
  exhaustive-raw, and exhaustive-visible seven-repeat comparisons;
- `benchmarks/results/multi-application-workload.json` — a three-device workload with
  multiple applications, ordinary variables, n-variable binding, two definitions in
  one rule, and one intentionally undefined source before provenance hardening;
- `benchmarks/results/multi-application-provenance.json` — the same workload after
  provenance-aware explanations and early propagation;
- `benchmarks/results/multi-application-evaluation-cache.json` — the same workload
  after exact thread-local evaluation reuse; and
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

### Solve and output decomposition

The final copy-family medians below are milliseconds from seven samples after one
warm-up. `exhaustive-raw` consumes every model without building visible model objects;
`exhaustive-visible` includes stable ordinary atoms, reconstructed assignments,
storage, sorting, and output normalization. Complete visible digests match in every
visible case.

| Values | Mode | Reference solve | Native solve | Native initialization |
| ---: | --- | ---: | ---: | ---: |
| 10 | first model | 0.050 | 0.416 | 0.323 |
| 10 | exhaustive raw | 0.063 | 0.564 | 0.324 |
| 10 | exhaustive visible | 0.312 | 0.710 | 0.394 |
| 1,000 | first model | 2.012 | 22.553 | 20.568 |
| 1,000 | exhaustive raw | 7.911 | 42.176 | 21.487 |
| 1,000 | exhaustive visible | 55.741 | 57.145 | 26.613 |
| 5,000 | first model | 11.255 | 401.796 | 377.729 |
| 5,000 | exhaustive raw | 687.646 | 1,262.722 | 342.981 |
| 5,000 | exhaustive visible | 2,919.185 | 1,575.660 | 482.028 |
| 10,000 | first model | 29.755 | 705.793 | 692.024 |
| 10,000 | exhaustive raw | 1,611.042 | 2,657.385 | 639.030 |
| 10,000 | exhaustive visible | 10,602.728 | 3,308.067 | 888.357 |

The first-model result isolates a large Python initialization cost: native search has
not yet amortized its approximately 692 ms setup at N=10,000. Exhaustive raw adds
roughly 1.95 seconds beyond first-model solve. Visible collection adds roughly 651 ms
beyond exhaustive raw when all surrounding solve costs are included. These are
different costs and none is presented as a grounding result.

Before incremental support tracking, N=1,000 caused one million check-time seed probes.
The final N=10,000 copy run records zero seed probes, 10,000 watched literal changes,
10,000 seed activations, 10,000 matching undo removals, 10,000 rule evaluations, and
no clauses. Application canonicalization turns 10,002 application decode requests
into two actual application decodes.

### Reconstruction profile

The pre-index N=10,000 visible profile attributed a 2.550-second median to
`model.symbols(atoms=True)` and 0.330 seconds to rendering ordinary atoms. The solver
now indexes non-private ordinary symbolic atoms once during initialization, watches
their solver literals, and trails only the atoms true in each thread. It no longer
calls `model.symbols()` per model. In the final N=10,000 profile the corresponding
timer placeholders are 1.289 ms and 1.503 ms across all 10,000 models. Other final
medians are:

| Component | N=10,000 median |
| --- | ---: |
| snapshot construction inside propagator | 66.293 ms |
| snapshot lookup | 40.499 ms |
| assignment rendering | 49.249 ms |
| undefined-state rendering | 7.097 ms |
| model storage | 15.685 ms |
| deterministic model sort | 7.018 ms |
| normalized digest | 9.312 ms |

Native exhaustive-visible solve falls from 6,496.681 ms in the pre-index profile to
3,308.067 ms in the final profile, a 49.1% reduction. This is a solver/output-path
improvement because the removed `model.symbols()` calls were made by the native solver
for normal visible models; digest calculation remains separately timed benchmark work.
Human and JSON model semantics are unchanged. The reference visible path also spends
heavily on Python symbol extraction, explaining why its output-inclusive timing is
much higher than its raw enumeration timing.

### Multi-application workload

The additional workload has three devices, two defined raw readings, one undefined
raw reading, per-device thresholds, a grounder-inert copy, a derived status, and a
two-n-variable readiness comparison. Its relational source omits a functionality
constraint that is provably redundant under the exactly-one choice; this avoids a
quadratic grounding artifact while preserving the exact model set.

| Candidate values | Reference rules | Native rules | Reference ground | Native ground | Reference solve | Native solve | Models equal |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 92 | 52 | 0.343 ms | 0.744 ms | 0.100 ms | 7.518 ms | yes |
| 100 | 812 | 232 | 1.306 ms | 1.547 ms | 0.622 ms | 74.496 ms | yes |
| 1,000 | 8,012 | 2,032 | 12.534 ms | 30.642 ms | 9.552 ms | 4,526.886 ms | yes |

The original result establishes that the structural advantage survives: the native
program still grounds the actual alternative seed assignments, but the dependent
copy/rules add fixed theory metadata per device instead of one relational rule per
candidate value. Absolute native solve performance is poor. At N=1,000 the prototype
performs 8,482 total checks and emits
7,482 broad clauses containing 7,504,446 literals, with maximum width 1,003. Visible
reconstruction is only 22.276 ms. This workload identifies broad guard explanations,
not model output or grounding, as the dominant accidental cost.

The post-hardening run uses the same workload and seven-sample protocol:

| Candidate values | Reference solve | Native solve | Total checks | Clauses | Broad clauses | Clause literals | Maximum width | Models equal |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 0.092 ms | 4.768 ms | 13 | 21 | 0 | 41 | 2 | yes |
| 100 | 0.622 ms | 35.392 ms | 103 | 201 | 0 | 401 | 2 | yes |
| 1,000 | 9.012 ms | 373.820 ms | 1,003 | 2,001 | 0 | 4,001 | 2 | yes |

These measurements remove the identified broad-clause pathology and reduce checks to
approximately one per model, while preserving exact normalized model digests. They do
not establish performance parity: at N=1,000 the native solve median remains about
41 times the relational reference median. The prior artifact used Clingo 5.8.1 and the
follow-up uses 5.8.2, so cross-artifact timing changes are informational; deterministic
clause counts and widths carry the optimization claim.

At commit `88c4f7fd6e09f50917bd683b8e2f2ce250d23cbd`, an exact thread-local
cache reuses the closure already computed during early propagation when no seed or rule
activation has changed. Activation and undo invalidate it. The same seven-sample
protocol records:

| Candidate values | Native solve before cache | Native solve with cache | Evaluation runs | Check cache hits | Rule-body evaluations | Models equal |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 4.768 ms | 3.846 ms | 18 | 13 | 162 | yes |
| 100 | 35.392 ms | 27.878 ms | 198 | 103 | 1,782 | yes |
| 1,000 | 373.820 ms | 303.996 ms | 1,998 | 1,003 | 17,982 | yes |

At N=1,000, rule-body evaluations fall 33.4% and the same-environment native median
falls 18.7%. The 8.972 ms relational reference median is still about 34 times faster.
The cache removes duplicate work; it does not make closure maintenance incremental.

### Conflict and thread audit

Direct seed functionality conflicts are detected incrementally and receive a clause
derived from the two incompatible support literals. Tests cover width two, unit, and
empty conflicts. Transitive support sets now give derived functionality conflicts and
comparison guards narrow explanations as well. Conflicting n-variable definitions
intentionally make that rule-local n-variable undefined; they are not themselves solver
conflicts. Static no-provider undefinedness has an empty proof, while dynamic absence
still has no general reason. The Python API accepts the resulting narrower clauses;
the remaining research problem is a compositional explanation design for absence and
wider derivation shapes rather than broadening clauses by assumption.

Clingo documents that one propagator instance can receive callbacks from different
solver threads. The experiment now shares only immutable decoded indexes and keeps
support maps and snapshots per thread. Exhaustive one-thread, two-thread, and repeated
two-thread runs of a 20-model, two-application copy family have identical normalized
models and balanced undo counts. The research solver is capped at two threads. This is
bounded feasibility evidence, not a proof against every race or a production support
claim; benchmark timings continue to use one thread.

Peak process memory was not recorded because the Python standard library has no
portable, comparable peak-process measure on all supported platforms. No extra
platform-specific dependency was added for this study.

## Environment

The final measurements record:

- benchmark date (UTC): 2026-08-11;
- final decomposition input commit: `d5d78a710505bc6f51ea9aaf1339499ffd046723`;
- multi-application input commit: `cd31d6885ec90a346d4fc794252957b13f7fc9b9`;
- provenance-hardening input commit: `1b8dd4f5076fefff76f7b086d63fbc6b227761fb`;
- evaluation-cache input commit: `88c4f7fd6e09f50917bd683b8e2f2ce250d23cbd`;
- Python: 3.12.13;
- Clingo: 5.8.1 for the completed feasibility measurements and 5.8.2 for the
  post-feasibility workloads;
- platform: Windows 11 (`10.0.26200`, AMD64);
- CPU: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel; and
- logical CPU count: 12.

All timing runs explicitly use one thread; two threads are tested semantically only.
Timings describe this machine and are informational. Deterministic rule/atom deltas,
work counters, and exact model digests are the primary evidence.

## GO decision

**PARTIAL GO for further research; NO-GO for production integration.**

The experiment proves the central feasibility proposition: theory metadata plus a
Python propagator can keep `_v` out of ordinary grounding, bind basic solver-time
values, preserve explicit undefinedness, restore state across backtracking, and keep
copy-rule grounding overhead constant for the measured family. Exact visible models
match the relation reference through 10,000 candidate values.

It does not satisfy every GO gate:

1. the full historical source frontend is not connected to this separate research IR;
2. n-loop detection is exact only for the variable-free constant-head subfragment and
   conservative for non-ground or dynamic-head programs;
3. two-thread behavior has bounded tests but not production-grade concurrency proof;
4. cross-type historical ordering semantics are not established;
5. derived values, comparisons, and guards have positive-support reasons, but dynamic
   undefinedness and wider derivations lack a general compositional provenance model;
6. native first-model and exhaustive solving remain slower than the relational
   reference even after reconstruction overhead was substantially reduced.

Accordingly there is no CLI flag, production import, version change, release, or claim
that ASPf-next now supports historical n-variables. The released reference backend and
language contract are unchanged.

## Exact next engineering questions

Before reconsidering integration:

1. extend the current support-set explanations into a compositional provenance design
   for dynamic undefinedness and wider derivations;
2. move exact n-loop analysis to grounded typed metadata while mapping witnesses back
   to source locations;
3. incrementally update affected closure state and reduce remaining Python callback,
   initialization, and raw-enumeration overhead;
4. stress the bounded two-thread design under substantially larger and conflicting
   workloads, or return to an explicit one-thread production boundary;
5. define how a production typed frontend represents rule-local n-variable identities
   after ordinary grounding; and
6. determine whether the remaining reason-tracking and callback costs justify a native
   Clingo extension rather than further Python micro-optimization.

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
4. **Is any performance claim based on one tiny run?** No. The scaling improvement is
   based on seven measured runs after one warm-up, with raw samples and IQRs retained
   at every size. The original one-shot large run remains equality-only evidence.
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
   values, every activated benchmark seed has a matching undo removal, blocked-branch
   tests do not leak state, snapshots are deleted, and repeated controls agree.
10. **Are n-loops distinguished from n-stratification and ordinary recursion?** Yes.
    The typed analysis and focused note cover direct/indirect paths, ordinary cycles,
    default-negated edges, full simple-term keys, and the conservative non-ground
    boundary.
11. **Are conflicts explained from relevant literals?** Direct and derived
    functionality plus defined comparison guards are; static no-provider
    undefinedness is exact, while dynamic absence remains an explicit gap.
12. **Is thread safety accurately stated?** Yes. One and two threads are accepted,
    timing remains one-thread, and the two-thread result is bounded evidence rather
    than a production proof.
13. **Are limitations disclosed?** Yes: research-only typed input, conservative wider
    n-loop coverage, incomplete dynamic-undefinedness provenance, bounded threading,
    unproved cross-type order, and slower absolute solving are explicit.
14. **Is model reconstruction counted honestly?** Yes. Raw enumeration, native visible
    reconstruction, stable sorting, and benchmark digest work have separate timers;
    normal visible semantics still take the deterministic path.
15. **Did a benchmark-only optimization leak into semantics?** No. Raw no-collection
    mode is opt-in to the research solver; normal collection and every released API
    remain unchanged.
16. **Did production ASPf-next behavior change?** No imports or execution paths were
    added under `src/aspf_next`, no CLI flag or `_V` syntax was added, and package
    version `0.2.0a1` is unchanged.
17. **Are grounding efficiency and solve speed separated?** Yes. Structural deltas,
    ground time, first-model solve, exhaustive raw solve, and visible output are
    reported independently.
18. **Would the report invite an ASP researcher to infer too much?** It should not:
    exactness is scoped to a small ground n-loop subfragment, historical ordering is
    unproved, and PARTIAL GO explicitly remains NO-GO for production integration.
