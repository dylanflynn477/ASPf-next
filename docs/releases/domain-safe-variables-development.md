# Domain-safe ordinary-variable development notes

Status: unreleased development increment. This work has not been assigned a
release number.

## Implemented boundary

ASPf-next accepts an ordinary uppercase variable only when it is one complete,
direct argument of a declared non-Herbrand application. Every such variable
must also occur in an ordinary, unnegated positive symbolic body atom in the
same rule:

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

The domain atom may occur before or after the n-atom. The rule applies to `#=`
assignment heads and to all six supported positive body operators. Right
operands remain ground.

## Source-safety rule

Safety is checked on the source rule before reference lowering. A generated
`__aspf_value/2` lookup or helper variable cannot make a source variable safe.
Neither can another n-atom, ordinary equality or comparison, a default-negated
atom, or a classically negated atom.

This is intentionally narrower than historical Clingo{f}'s equality-provided
safety. The restriction gives the modern Clingo grounder an independent finite
domain for every variable used to construct a non-Herbrand key without silently
inventing historical behavior.

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

## Still unsupported

- ordinary variables as assignment values or comparison right operands;
- ordinary variables nested in compound key arguments;
- variables whose only apparent domain comes from another n-atom, equality,
  comparison, negation, a head, an aggregate, a choice, a conditional literal,
  or a disjunction;
- anonymous `_` inside n-atoms;
- `_V`-style non-Herbrand variables;
- arithmetic, intervals, pools, or tuples inside n-atoms;
- application-to-application comparisons;
- default-negated n-atoms and broader n-atom contexts; and
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
