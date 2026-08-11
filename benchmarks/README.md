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
