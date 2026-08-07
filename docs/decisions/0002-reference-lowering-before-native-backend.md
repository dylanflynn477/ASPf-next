# 0002: Reference lowering before a native backend

Status: Accepted

## Context

Milestone 0.1 needs executable semantics that are easy to inspect and compare.
A theory-atom backend or custom propagator would add solver integration risk
before the compatibility boundary has a conformance foundation.

## Decision

Lower validated n-atoms to the private `__aspf_value/2` relation and enforce
functionality with an ordinary integrity constraint. Treat this as the
correctness-oriented reference backend. Defer any native theory/propagator
backend to a separately reviewed design that is tested for answer-set
equivalence against the reference backend.

## Consequences

- `--emit-lowered` exposes the complete executable translation.
- The backend makes no historical grounding-efficiency claim.
- Some programs may ground less efficiently than a specialized implementation.
- Future backends can share the scanner, typed IR, diagnostics, and model
  normalizer without changing the established reference oracle.

See the implemented [pipeline](../architecture.md).
