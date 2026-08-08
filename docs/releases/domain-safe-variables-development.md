# Domain-safe ordinary-variable implementation history

Status: Included in `0.2.0a1`. This document records the initial independent
domain increment and its later seed-equality expansion.

## Implemented boundary

ASPf-next accepts an ordinary uppercase variable when it is one complete,
direct argument of a declared non-Herbrand application. The initial increment
required every such variable to occur in an ordinary, unnegated positive
symbolic body atom in the same rule:

```asp
#nherb balance/1.
account(checking;savings).

low(A) :-
    account(A),
    balance(A) #< 1000.

balance(A) #= 0 :-
    account(A),
    empty(A).
```

The domain atom may occur before or after the n-atom. The later historical
seed-safety increment also accepts a positive scalar seed equality such as
`balance(A) #= V` as a domain for its direct key variables and optional complete
value variable. Dependent comparisons and default negation do not supply
safety.

## Source-safety rule

Safety is checked on the source rule before reference lowering. A generated
`__aspf_value/2` lookup or helper variable cannot make a source variable safe.
Only an accepted ordinary positive symbolic atom or positive scalar seed
equality can supply this source safety; dependent n-atoms, default-negated
atoms, and classically negated atoms cannot.

The original independent-domain rule was intentionally narrower than
historical Clingo{f}. The later seed-equality implementation reproduces the
documented P1 safety case through the finite positive value relation, without
adding a global value universe or allowing dependent comparisons to bind.

## Reference lowering

For example:

```asp
low(A) :- account(A), balance(A) #< 1000.
```

lowers to the equivalent of:

```asp
low(A) :-
    account(A),
    __aspf_value(balance(A),_AspfCmp0),
    __aspf_integer(_AspfCmp0),
    _AspfCmp0 < 1000.
```

Clingo grounds `A` through `account(A)`. The private lookup checks a grounded
key but does not define it: missing `__aspf_value/2` still means undefined.
Functionality continues to prohibit two distinct values for the same grounded
key.

## Current unsupported boundary

- ordinary variables as assignment-head values or ordered-comparison operands;
- ordinary variables nested in compound key arguments;
- variables whose only apparent domain comes from a dependent n-atom,
  default negation, a head, an aggregate, a choice, a conditional literal, or
  a disjunction;
- anonymous `_` inside n-atoms;
- `_V`-style non-Herbrand variables;
- arithmetic, intervals, pools, or tuples inside n-atoms;
- broader n-atom contexts; and
- a native theory-atom or propagator backend.

Each rejected form receives a filename-, line-, and column-aware diagnostic.
Comments and strings remain inert.

## Evidence and tests

The primary-source analysis and the reason for choosing this conservative
subset are recorded in the [variable semantics research](../design/variable-semantics.md)
and [milestone plan](../design/variable-milestone-plan.md). The implementation
has focused frontend, lowering, solver, CLI, example, and manifest-driven
conformance coverage, including multi-file rules, partiality, functionality,
all supported operators, comments, strings, multiline layout, and every
variable rejection category above.

This reference translation makes no claim to the grounding-efficiency behavior
of historical Clingo{f}.
