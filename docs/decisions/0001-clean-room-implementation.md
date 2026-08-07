# 0001: Clean-room implementation

Status: Accepted

## Context

ASPf-next revives a historical language surface while using modern Clingo. The
historical Clingo{f} implementation is not a dependency and its code provenance
must not become entangled with this repository.

## Decision

Implement ASPf-next independently from public language papers, public user
documentation, and the supported Clingo Python API. Do not copy, port,
translate, or mechanically reproduce historical Clingo{f} source code. Record
the primary source behind each semantic claim in the
[traceability matrix](../specification-traceability.md).

## Consequences

- Historical behavior that cannot be verified remains undocumented or rejected.
- Compatibility gaps are expected and must be named rather than concealed.
- Contributions need provenance and tests appropriate to any semantic change.
- Historical source code cannot be used as a shortcut when implementing a
  parser, lowering, or future backend.

See the detailed [provenance policy](../provenance.md).
