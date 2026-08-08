# Positive ground ordered-comparison implementation history

## Status

Included in `0.2.0a1`. This document preserves the boundary at the time the
increment was implemented; the supported-language document is normative.

## Added surface

The frontend accepts `#<`, `#<=`, `#>`, and `#>=` only as complete, positive,
fully ground rule-body literals:

```asp
#nherb temperature/1.
temperature(freezer) #= -5.
below_zero :- temperature(freezer) #< 0.
```

The left operand must be a declared ground non-Herbrand application, and the
right operand must be an integer literal. The comparison is true only when the
application has a defined integer value and the usual arithmetic relation holds.
Undefined, symbolic, and string values make it false. No coercion is performed.

At the time this increment was completed, variables remained rejected inside
n-atoms. The later domain-safe-variable increment supersedes that restriction
for direct key arguments only.

## Reference lowering

Integer assignments add a private type marker:

```asp
__aspf_value(temperature(freezer),-5).
__aspf_integer(-5).
```

The body comparison lowers to the equivalent of:

```asp
__aspf_value(temperature(freezer),_AspfCmp0),
__aspf_integer(_AspfCmp0),
_AspfCmp0 < 0
```

The value lookup enforces definedness, and the private marker enforces the
integer-only boundary before Clingo evaluates the relation. One shared lowering
path handles all four typed operators.

Private `#defined` directives prevent intentionally false lookup cases from
printing internal predicate names in Clingo informational diagnostics. They do
not derive values or alter partiality.

## Boundary at this increment

The following list records the boundary when ordered comparisons were first
added. Later development notes may supersede individual items.

- ordered comparisons in facts or rule heads;
- default-negated ordered comparisons;
- non-integer right operands or numeric coercion;
- comparisons between two non-Herbrand applications;
- variables or arithmetic inside n-atoms;
- n-atoms in aggregates, choices, conditional literals, or disjunctions; and
- theory atoms, a native propagator, or any grounding-efficiency claim.

See the [supported-language document](../supported-language.md) for the
normative boundary and the [traceability matrix](../specification-traceability.md)
for the primary semantic basis. The later
[domain-safe variable notes](domain-safe-variables-development.md) document the
narrow variable subset now accepted in ordered keys.
