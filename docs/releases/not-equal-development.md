# Positive ground `#!=` implementation history

## Status

Included in `0.2.0a1`. This document preserves the boundary at the time the
increment was implemented; the supported-language document is normative.

## Added surface

The frontend accepts `#!=` only when it is a complete, positive, ground rule-body
literal:

```asp
#nherb balance/1.
balance(account1) #= 500.
different :- balance(account1) #!= 600.
```

The left operand must be a declared ground non-Herbrand application. The right
operand must be an integer, symbolic constant, or string. The literal is true
only when the application has a defined value different from the right operand.
If the application is undefined, the literal is false.

## Reference lowering

The body literal above lowers to the equivalent of:

```asp
__aspf_value(balance(account1),_AspfNeq0), _AspfNeq0 != 600
```

The lookup atom enforces definedness before the ordinary Clingo comparison.
ASPf-next does not lower `#!=` to `not __aspf_value(...)` and does not interpret
it as negation-as-failure.

## Boundary at this increment

At the time this increment was completed, the following constructs were still
unsupported. Later development notes may supersede individual items.

- `#!=` in facts or rule heads;
- default-negated `#!=`;
- application-to-application comparisons;
- variables or arithmetic inside n-atoms;
- n-atoms in aggregates, choices, conditional literals, or disjunctions;
- `#<`, `#<=`, `#>`, and `#>=`; and
- theory atoms, a native propagator, or any grounding-efficiency claim.

See the [supported-language document](../supported-language.md) for the
normative boundary and the [traceability matrix](../specification-traceability.md)
for the primary semantic basis.
