# Positive ground ordered-comparison development notes

## Status

This is an unreleased development increment. It has not been assigned a release
number and does not change the `0.1.0a1` package metadata.

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

Variables remain rejected inside n-atoms. The ordinary ASP portions of a rule
may still contain variables, but the application in an ordered n-atom must be
fully ground.

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

## Still unsupported

- ordered comparisons in facts or rule heads;
- default-negated ordered comparisons;
- non-integer right operands or numeric coercion;
- comparisons between two non-Herbrand applications;
- variables or arithmetic inside n-atoms;
- n-atoms in aggregates, choices, conditional literals, or disjunctions; and
- theory atoms, a native propagator, or any grounding-efficiency claim.

See the [supported-language document](../supported-language.md) for the
normative boundary and the [traceability matrix](../specification-traceability.md)
for the primary semantic basis.
