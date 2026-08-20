# Native versus reference n-variable copy benchmark

## Question

Does a ground theory representation avoid the candidate-domain expansion caused by
the relational approximation of a grounder-inert non-Herbrand variable?

The experiment measures one selected source value and a copy equivalent to:

```asp
h(x) #= _v :- f(x) #= _v.
```

The reference copy is:

```asp
__bench_value(h(x),V) :- __bench_value(f(x),V).
```

The experimental copy records `_v` as the ground theory term `nvar(v)` and evaluates
its definition in the propagator. It does not emit `_v` as an ordinary Clingo variable.

## Method

Candidate-domain sizes are 10, 100, 1,000, 5,000, and 10,000. Each baseline chooses
exactly one candidate source value. Copy overhead is the copy program's structural
count minus the corresponding no-copy baseline; this avoids crediting the native path
for unavoidable source alternatives.

The main metrics are deterministic observer callbacks and atom-universe counts:

- grounded ordinary/weight rules;
- ordinary symbolic atoms;
- theory atoms; and
- copy deltas for each representation.

Grounding-only runs use one warm-up and seven measured runs at all five sizes. They do
not solve or make a model-count claim. The original total-rescan implementation has
complete solve measurements through 1,000; its larger repeated attempts were stopped
as resource-unreasonable. The incremental implementation uses one warm-up and seven
measured exhaustive runs at all five sizes. Timing is reported as median and IQR and
is not a test threshold.

Every measured solve uses one Clingo thread. The runners reject structural or model
count drift between repeats. Model equivalence compares sorted user-visible ordinary
atoms and reconstructed ASP{f} assignments, excluding all private relation/theory
atoms. Result files store SHA-256 digests of the exact sorted model sets.

Portable peak process memory is not available from Python's standard library across
the supported platforms. It was omitted rather than adding a platform-specific
measurement with misleading comparability.

## Environment

| Field | Value |
| --- | --- |
| Date (UTC) | 2026-08-11 |
| Original input commit | `3d04ee1ddc717428800b11a79f3888e0c2311601` |
| Incremental input commit | `9162315c97d332fb8be196445841cf54e44f748a` |
| Python | 3.12.13 |
| Clingo | 5.8.1 |
| Platform | Windows 11, build 10.0.26200, AMD64 |
| CPU | Intel64 Family 6 Model 186 Stepping 3, GenuineIntel |
| Logical CPUs | 12 |
| Solver threads | 1 |

## Structural result

| Values | Reference baseline rules | Reference copy rules | Reference rule delta | Reference atom delta | Native baseline rules | Native copy rules | Native rule delta | Native theory-atom delta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 14 | 24 | 10 | 10 | 14 | 15 | 1 | 1 |
| 100 | 104 | 204 | 100 | 100 | 104 | 105 | 1 | 1 |
| 1,000 | 1,004 | 2,004 | 1,000 | 1,000 | 1,004 | 1,005 | 1 | 1 |
| 5,000 | 5,004 | 10,004 | 5,000 | 5,000 | 5,004 | 5,005 | 1 | 1 |
| 10,000 | 10,004 | 20,004 | 10,000 | 10,000 | 10,004 | 10,005 | 1 | 1 |

The relational copy adds one ground rule and one ordinary symbolic atom per candidate.
The experimental copy adds one ground rule and one theory atom at every tested size.
This is the desired grounding-growth result. It is not a claim that the complete native
program is constant-size: both baselines contain the actual candidate source choices.

Median grounding-only copy times in milliseconds:

| Values | Reference median | Reference IQR | Native median | Native IQR |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 0.118 | 0.009 | 0.209 | 0.010 |
| 100 | 0.496 | 0.014 | 0.630 | 0.023 |
| 1,000 | 4.515 | 0.065 | 5.059 | 0.324 |
| 5,000 | 23.180 | 0.940 | 26.840 | 1.483 |
| 10,000 | 47.343 | 0.636 | 51.522 | 2.233 |

These tiny platform-specific times support no speed claim. The observer deltas, not
the elapsed differences, establish the structural conclusion.

## Original solve result and profile

Seven-run exhaustive copy measurements in milliseconds:

| Values | Reference ground median | Native ground median | Reference solve median | Native solve median | Models per run | Equal model sets |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 0.145 | 0.223 | 0.066 | 0.859 | 10 | yes |
| 100 | 0.517 | 0.703 | 0.445 | 13.537 | 100 | yes |
| 1,000 | 4.503 | 6.170 | 7.322 | 1,193.182 | 1,000 | yes |

Exact one-shot model equality also passes at 5,000 and 10,000. At 10,000 the native
and reference normalized model-set digest is:

```text
7116ab0518c86a39935e32bd7bed83f77fe663eab7201f7299e5cf038ebab5fc
```

The separate 5,000/10,000 equivalence command took approximately 140 seconds in total,
but that duration is deliberately not recorded as a comparative timing sample.

The solve data exposes the prototype's dominant limitation. It reconstructs native
state from every candidate seed literal at every total assignment. In this family,
that is approximately O(candidate literals × enumerated models). A repeated run aimed
at 10,000 was stopped after more than four minutes, and a repeated run aimed at 5,000
was stopped after more than three minutes. Neither aborted run wrote a result, and no
partial measurements are included.

A reproducible `cProfile` run at N=1,000 confirmed the hypothesis rather than merely
assuming it: `NativePropagator.check` made 1,002,000 calls through `_true` to
`Assignment.value`; 1,000,000 were candidate-seed probes. The profiled check path took
3.172 seconds cumulative under profiler instrumentation, while initialization was
about 0.100 seconds and model rendering was much smaller. The exact source state is
the original result commit above.

## Incremental solve result

The optimized propagator builds immutable lookup structures during initialization,
watches only the signed literal that means a native theory atom is true, and maintains
per-thread application support counts from `propagate`/`undo` deltas. Total checks copy
the active supports rather than scanning candidates. An application-dependency queue
evaluates providers before consumers and requeues only affected rules. An
initialization-local theory-term cache canonicalizes repeated application keys without
surviving the solve or merging distinct values.

Seven-run exhaustive copy measurements in milliseconds:

| Values | Reference ground | Native ground | Reference solve | Native solve | Native total | Equal models |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 0.145 | 0.711 | 0.066 | 2.801 | 7.112 | yes |
| 100 | 0.527 | 1.629 | 0.432 | 12.192 | 15.663 | yes |
| 1,000 | 4.801 | 12.799 | 7.613 | 155.543 | 174.861 | yes |
| 5,000 | 37.341 | 60.942 | 593.375 | 1,597.811 | 1,669.417 | yes |
| 10,000 | 93.833 | 131.346 | 1,300.900 | 4,188.990 | 4,364.925 | yes |

The N=1,000 native median is 7.67× faster than the original 1,193.182 ms median.
Tiny-case setup overhead is larger and no universal speedup is claimed. The optimized
native implementation remains slower than the reference at every measured size.

Deterministic native-copy work counters:

| Values | Full seed probes in checks | Propagated literals | Seed add/remove pairs | Rule evaluations | Application requests / actual decodes |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0 | 10 | 10 | 10 | 12 / 2 |
| 100 | 0 | 100 | 100 | 100 | 102 / 2 |
| 1,000 | 0 | 1,000 | 1,000 | 1,000 | 1,002 / 2 |
| 5,000 | 0 | 5,000 | 5,000 | 5,000 | 5,002 / 2 |
| 10,000 | 0 | 10,000 | 10,000 | 10,000 | 10,002 / 2 |

At N=10,000, median initialization is 449.380 ms and eager model reconstruction is
2,004.245 ms. A final profiled N=5,000 run reports 0.305 seconds cumulative in
propagator initialization, 0.205 seconds in all total checks, 0.195 seconds in Clingo
model-symbol extraction, and 0.081 seconds in rule bodies. Costs are now distributed;
there is no remaining single full-domain check-time loop to remove.

Those figures are the pre-decomposition incremental baseline. A later profile found
that per-model `model.symbols()` scans dominated the reported reconstruction number.
Indexing visible literals once and trailing true atoms reduces final N=10,000 native
exhaustive-visible median from 6,496.681 to 3,308.067 ms. Final first-model,
exhaustive-raw, and exhaustive-visible native medians are 705.793, 2,657.385, and
3,308.067 ms respectively; the corresponding reference medians are 29.755, 1,611.042,
and 10,602.728 ms. The reference visible figure also contains Python symbol extraction
and is not a search-speed comparison.

## Post-feasibility provenance workload

The original multi-application workload isolated broad guard clauses as the dominant
remaining solver cost. A follow-up at commit
`1b8dd4f5076fefff76f7b086d63fbc6b227761fb` uses the same generated programs, one
warm-up, seven samples, and one solver thread after support-set provenance and early
propagation were added. It ran on the recorded Windows/Intel environment above with
Python 3.12.13 and Clingo 5.8.2 on 2026-08-20.

| Values | Reference solve | Native solve | Checks | Clauses | Broad | Clause literals | Max width | Equal models |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 0.092 ms | 4.768 ms | 13 | 21 | 0 | 41 | 2 | yes |
| 100 | 0.622 ms | 35.392 ms | 103 | 201 | 0 | 401 | 2 | yes |
| 1,000 | 9.012 ms | 373.820 ms | 1,003 | 2,001 | 0 | 4,001 | 2 | yes |

The deterministic work counters demonstrate that the broad-clause pathology is gone
for this workload. Timing is not a controlled claim against the older Clingo 5.8.1
artifact, and the current native median remains about 41 times the current reference
median at N=1,000.

A second follow-up at commit `88c4f7fd6e09f50917bd683b8e2f2ce250d23cbd`
reuses a thread's unchanged early evaluation at its total check. This is an exact cache,
not a semantic approximation: seed/rule activation and undo invalidate it.

| Values | Native solve before cache | Native solve with cache | Evaluation runs | Check cache hits | Rule-body evaluations | Equal models |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 10 | 4.768 ms | 3.846 ms | 18 | 13 | 162 | yes |
| 100 | 35.392 ms | 27.878 ms | 198 | 103 | 1,782 | yes |
| 1,000 | 373.820 ms | 303.996 ms | 1,998 | 1,003 | 17,982 | yes |

At N=1,000 this removes 33.4% of rule-body evaluations and reduces the same-environment
native median by 18.7%. The clause result remains 2,001 narrow clauses, zero broad
clauses, 4,001 literals, and maximum width two. Profiled closure evaluation is still
the main Python callback cost; the 8.972 ms reference median remains much faster.

## Commands

Run from the repository root with the environment's Python:

```console
python -m benchmarks.structural_scaling \
  --sizes 10 100 1000 5000 10000 \
  --warmups 1 --repeats 7 \
  --output benchmarks/results/structural-scaling.json

python -m benchmarks.native_vs_reference \
  --sizes 10 100 1000 5000 10000 \
  --warmups 1 --repeats 7 \
  --output benchmarks/results/native-vs-reference-incremental.json

python -m benchmarks.equivalence_scaling \
  --sizes 5000 10000 \
  --output benchmarks/results/large-model-equivalence.json

python -m benchmarks.solve_decomposition \
  --sizes 10 100 1000 5000 10000 \
  --warmups 1 --repeats 7 \
  --output benchmarks/results/solve-decomposition-final.json

python -m benchmarks.multi_application_workload \
  --sizes 10 100 1000 --warmups 1 --repeats 7 \
  --output benchmarks/results/multi-application-evaluation-cache.json
```

Raw result files:

- [`benchmarks/results/structural-scaling.json`](../../benchmarks/results/structural-scaling.json)
- [`benchmarks/results/native-vs-reference.json`](../../benchmarks/results/native-vs-reference.json)
- [`benchmarks/results/native-vs-reference-incremental.json`](../../benchmarks/results/native-vs-reference-incremental.json)
- [`benchmarks/results/large-model-equivalence.json`](../../benchmarks/results/large-model-equivalence.json)
- [`benchmarks/results/solve-decomposition-before-visible-index.json`](../../benchmarks/results/solve-decomposition-before-visible-index.json)
- [`benchmarks/results/solve-decomposition-after-visible-index.json`](../../benchmarks/results/solve-decomposition-after-visible-index.json)
- [`benchmarks/results/solve-decomposition-final.json`](../../benchmarks/results/solve-decomposition-final.json)
- [`benchmarks/results/multi-application-workload.json`](../../benchmarks/results/multi-application-workload.json)
- [`benchmarks/results/multi-application-provenance.json`](../../benchmarks/results/multi-application-provenance.json)
- [`benchmarks/results/multi-application-evaluation-cache.json`](../../benchmarks/results/multi-application-evaluation-cache.json)

## Interpretation and limitations

The theory/propagator representation materially improves copy-rule grounding growth,
preserves the tested visible models, and no longer performs candidate-domain rescans
at every model. It remains slower for first-model and raw exhaustive solving. The
largest avoidable visible-output scan has been removed. The original multi-application
result then exposed broad guard clauses; provenance-aware support sets and early
propagation remove that pathology in the follow-up run. This is evidence that
grounder-inert metadata and narrow positive-support explanations are possible through
the Python API, not evidence that this implementation is production-ready or faster
than the mature relational reference.

The copy family isolates one important historical motivation. The additional
three-device workload exercises several applications, ordinary variables, partial
undefinedness, a copy, two n-variable definitions, and several rules; at N=1,000 it
grounds 2,032 native versus 8,012 reference rules with exact models, but solves in
4,526.886 versus 9.552 ms because it generates 7,482 broad clauses. The research
artifact is retained as the pre-provenance baseline. The follow-up run preserves exact
models and grounding structure while reducing the native result to 2,001 narrow
clauses, zero broad clauses, 4,001 clause literals, maximum width two, and a 373.820 ms
solve median. Exact evaluation reuse further reduces the final median to 303.996 ms
without changing those clause metrics. The 8.972 ms reference median remains about
34 times faster. The research report documents the semantic, explanation, threading,
and n-loop boundaries.
