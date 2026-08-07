# 0005: Reserved backend namespace

Status: Accepted

## Context

The reference lowering introduces ordinary Clingo predicates, currently
`__aspf_value/2`. If a user can define the same predicate or a future internal
name, user semantics can collide with functionality enforcement or model
reconstruction.

## Decision

Reserve every executable identifier beginning with `__aspf_`. Reject user
occurrences during frontend validation while leaving matching text in comments
and quoted strings inert. Hide internal predicates from normalized output.

## Consequences

- Backend predicates cannot be spoofed by a source program.
- The project may add internal predicates without narrowing the user namespace
  again.
- Programs that previously used this prefix as ordinary Clingo identifiers must
  rename them to run through ASPf-next.
- The rule is an ASPf-next engineering boundary, not historical ASP{f}
  semantics.

The corresponding implementation and conformance cases are indexed in the
[traceability matrix](../specification-traceability.md).
