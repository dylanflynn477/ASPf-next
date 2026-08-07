# 0003: Partial rather than total functions

Status: Accepted

## Context

Primary ASP{f} semantics allows incomplete information about a function: a
ground application can lack a value in an answer set. Automatically choosing a
value would change both the knowledge represented and the resulting models.

## Decision

Do not derive a value from a declaration and do not add a totality rule. A key
is defined exactly when its value assignment is present. A positive body
equality is false when the key is undefined.

## Consequences

- `#nherb f/n.` alone produces no assignment.
- Undefinedness is observable as absence in normalized models.
- Functionality constrains competing values but never requires one.
- Comparisons added later must distinguish undefinedness from a defined,
  nonmatching value.

The historical basis and implementation mapping are recorded in the
[partiality rows](../specification-traceability.md).
