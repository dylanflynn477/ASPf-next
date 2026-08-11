# Native-backend feasibility benchmarks

These runners measure deterministic grounding structure as the primary evidence and
repeat timings as secondary, informational evidence. They are research tools, not
package entry points.

Run the relational reference baseline from the repository root:

```console
python -m benchmarks.reference_scaling \
  --sizes 10 100 1000 5000 10000 \
  --warmups 1 \
  --repeats 7 \
  --output benchmarks/results/reference-scaling.json
```

Each case is solved exhaustively. The JSON includes observer rule counts, symbolic and
theory atom counts, Clingo's post-grounding rule/atom/body statistics, model count,
raw timing samples, median/IQR summaries, runtime versions, platform data, date, and
commit. The runner rejects structural or model-count drift between repeats.

The family has exactly one selected value for `f(x)`. Its copy variant adds:

```asp
__bench_value(h(x),V) :- __bench_value(f(x),V).
```

Thus the visible semantic expectation is one copied `h(x)` value in every model. A
native runner will use the same candidate choices and visible expectation; it must not
use an ordinary variable for the copy.

Peak process memory is deliberately omitted: the Python standard library does not
provide a portable, comparable peak measurement across the project's supported
platforms. Timing results should not be used as hard test thresholds.

After the research prototype is available, run the paired experiment:

```console
python -m benchmarks.native_vs_reference \
  --sizes 10 100 1000 5000 10000 \
  --warmups 1 \
  --repeats 7 \
  --output benchmarks/results/native-vs-reference-incremental.json
```

The native baseline has the same exactly-one candidate choices and source assignments.
Its copy variant adds one typed n-variable rule represented by theory metadata. The
runner compares each encoding to its own no-copy baseline and exhaustively compares
normalized visible copy models. SHA-256 digests make the compared model sets auditable
without duplicating every model in the result file. Native measurements also record
separate propagator-initialization and model-reconstruction timings plus deterministic
counts for decode-cache activity, watched literal changes, seed support updates, total
checks, rule evaluations, blocking clauses, snapshots, and undo work.

Separate solver/search cost from output cost with:

```console
python -m benchmarks.solve_decomposition \
  --sizes 10 100 1000 5000 10000 \
  --warmups 1 --repeats 7 \
  --output benchmarks/results/solve-decomposition-final.json
```

Each representation is measured in first-model, fixed-ten, exhaustive-raw, and
exhaustive-visible modes. Raw mode consumes models without constructing visible model
objects. Visible mode retains deterministic rendering and exact digest equality. The
native profile separately records initialization, snapshot construction, lookup,
ordinary-symbol handling, assignment rendering, storage, sorting, and digest work.

The original total-rescan result remains in `native-vs-reference.json` and is limited
to sizes through 1,000. The incremental result covers all five sizes with the same
repeat policy. Grounding-only structure and the original untimed large equivalence
record remain independently reproducible:

```console
python -m benchmarks.structural_scaling \
  --sizes 10 100 1000 5000 10000 --warmups 1 --repeats 7 \
  --output benchmarks/results/structural-scaling.json

python -m benchmarks.equivalence_scaling \
  --sizes 5000 10000 \
  --output benchmarks/results/large-model-equivalence.json
```

The structural runner does not solve or report a model count. The equivalence runner
does not report timing: it performs one exact comparison of complete normalized model
sets. Keeping these questions separate preserves the original preregistered evidence
while the optimized paired runner now measures the large cases directly.

The less synthetic observation-pipeline workload is reproducible with:

```console
python -m benchmarks.multi_application_workload \
  --sizes 10 100 1000 --warmups 1 --repeats 7 \
  --output benchmarks/results/multi-application-workload.json
```

It uses three ordinary-grounded devices, multiple non-Herbrand applications, an
n-variable copy, one undefined source, a derived status, and a two-n-variable
comparison. The paired reference and native programs have exact normalized model-set
digests. Its exactly-one choice makes application conflicts impossible, so the
reference source deliberately omits a redundant functionality constraint that would
otherwise introduce an unrelated quadratic grounding artifact.
