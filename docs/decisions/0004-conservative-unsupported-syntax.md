# 0004: Conservative rejection of unsupported syntax

Status: Accepted

## Context

Historical ASP{f} includes variables, arithmetic, additional comparisons,
aggregates, defaults, and other constructs whose exact interaction is outside
milestone 0.1. Passing those fragments to Clingo or approximating them can
silently assign unintended Herbrand semantics.

## Decision

Accept only syntax with an explicit typed-IR representation and tested lowering.
Reject unsupported or ambiguous ASP{f}-shaped syntax with filename, line, and
column information. Keep comments and quoted strings inert.

## Consequences

- The implemented language is intentionally narrower than historical ASP{f}.
- Every future widening needs a primary-source basis, IR change, diagnostics,
  conformance fixtures, and backend tests.
- Some historically valid programs fail early instead of being partially
  interpreted.
- Ordinary Clingo remains pass-through only when no reserved ASP{f} meaning is
  implicated.

The exact current boundary is listed in the
[supported-language document](../supported-language.md).
