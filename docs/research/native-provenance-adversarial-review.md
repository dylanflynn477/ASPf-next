# Native provenance adversarial review

This review compares `main` at `1089ed3` with the candidate research milestone
`8c3e1c0` (`codex/native-provenance-hardening`). It tests the candidate as an
untrusted solver change. The released frontend and reference backend are unchanged.

## Verdict

The result remains **PARTIAL GO for research and NO-GO for production integration**.
No narrow learned clause was found that excludes a valid reference model in the
claimed research subset. One real clause-lifecycle defect was found: an unlocked broad
fallback clause was remembered forever even though Clingo may delete unlocked clauses.
The remembered entry could then suppress re-adding a required fallback. This is an
invalid-completion risk, not evidence that a valid answer set was excluded. Broad
fallbacks are no longer entered in the permanent learned-clause cache; narrow clauses
remain locked and may be deduplicated.

The candidate's positive provenance composition survived exhaustive and metamorphic
attacks involving alternative agreeing paths, diamonds, conditional definitions,
conflicts, comparisons, default negation, undefined operands, defined zero, undo,
repeated solving, rule/seed reordering, and one- versus two-thread model enumeration.

## Clause and cache audit

The propagator has an opt-in, one-thread clause audit. Each record identifies the
semantic conflict or guard, signed support literals, their seed/rule origin, the
required guard literal, final clause, and whether the clause is locked. Normal solving
does not collect or display these records.

Tests reconstruct every audited narrow clause from its recorded antecedent. Irrelevant
ordinary facts and choices do not enter the reasons. Multiple derivations of one value
retain a sufficient deterministic support; global minimum-cardinality explanations are
not claimed.

Cache invalidation is now explicit. Each thread owns a monotonic semantic generation.
Seed/rule activation and undo advance it; a cached positive closure is reusable only
when its generation matches. Stale-cache rejections and state changes are counted.
Branch-local negative evidence is never stored in that cache.

## Dynamic undefinedness

The review adds a conservative compositional proof for a useful dynamic fragment. An
application is explainably absent only when every grounded seed and assignment-rule
provider has an independently justified failure. A provider can fail because its
activation literal is actually false, its semantic body has a sufficient failure
reason, or its head expression has a sufficient undefined/conflict reason. A least
fixed point composes those facts through copy chains.

This analysis runs only at a total check. Clingo can retain don't-care literals there,
so an unassigned provider remains unknown and forces the existing broad fallback. A
cycle cannot bootstrap its own absence proof. This is deliberately narrower than
closed-world reasoning: lack of a positive value is never itself evidence.

## Differential evidence

The new deterministic matrix exhausts 144 small combinations of:

- left/right application values in `{undefined, 0, 1}`;
- equality and inequality;
- positive and default-negated comparison; and
- zero through three rule-local n-variables.

Every complete normalized native model set equals the independently written relational
reference set. Additional tests cover two independent same-value paths, derivation
diamonds, a `defined -> undefined -> conflict -> defined` branch sequence, two operand
provenance sets, agreeing definitions, derived functionality, irrelevant facts,
consistent rule-identifier renaming, seed/rule reordering, repeated controls, and one-
versus two-thread enumeration.

## N-loop precision

The non-ground matcher now performs rule-scoped unification instead of independent
per-position wildcard matching. It rejects impossible matches such as `p(X,X)` with
`p(a,b)` and preserves one ordinary-variable binding across an n-atom's application key
and scalar value. This reduces conservative false positives. The exact class is still
the documented variable-free constant-head fragment; source-level analysis still
cannot prove that every compatible non-ground path has a realizable grounded join.

## Benchmark result

Two same-machine, Python 3.12.13, Clingo 5.8.2 artifacts compare candidate commit
`8c3e1c0` with the hardened implementation. The workload has N distinct conditional
sources, N independent copy rules to one target, one model with all providers absent,
and complete reference/native model-set comparison.

| Providers | Candidate solve | Hardened solve | Broad clauses | Hardened broad | Clause literals before/after | Max width before/after |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 3.081 ms | 3.518 ms | 3 | 0 | 76 / 62 | 12 / 11 |
| 50 | 34.564 ms | 37.346 ms | 3 | 0 | 356 / 302 | 52 / 51 |
| 100 | 121.390 ms | 128.139 ms | 3 | 0 | 706 / 602 | 102 / 101 |

All model digests match. The narrower proof adds rule-body evaluation work and costs
about 5–14% on this intentionally adversarial family. This is a semantic/explanation
quality gain, not a solve-speed claim. The existing three-device workload is unchanged:
its undefined source was already statically provable, so dynamic analysis does not run
and its deterministic work counts remain identical.

## `_v` readiness

Real frontend exposure remains premature.

| Area | Current blocker |
| --- | --- |
| Semantic | The tested equality/inequality/integer-order fragment is bounded; historical cross-type order and wider rule forms are not established. |
| Parser/IR | The production IR has no rule-local n-variable identity or typed definition node; the research IR is intentionally separate. |
| Solver architecture | Positive closure is recomputed rather than incrementally maintained; dynamic absence adds a second compositional pass. |
| N-loops | Exact only for the variable-free constant-head fragment; non-ground matching is more precise but remains conservative. |
| Performance | Python closure evaluation dominates profiles; the new absence proof trades narrower clauses for extra evaluation work. |
| Threading | Two-thread model equality is bounded evidence. Clause auditing is intentionally one-thread deterministic. |
| Diagnostics | No source adapter maps grounded native rules, explanation gaps, or n-loop witnesses back through production source spans. |
| Compatibility | There is no executable historical `_v` corpus through the real frontend and no justified claim beyond the isolated research IR. |

The shortest defensible next step is not a CLI backend switch. It is incremental,
dependency-indexed closure/absence maintenance plus grounded typed n-loop metadata with
source provenance, followed by another differential and concurrency review.
