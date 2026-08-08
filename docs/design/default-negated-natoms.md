# Default-negated n-atoms

Status: implementation contract for `historical-default-negation`.

## Primary-source contract

Balduccini 2012 section 3, printed pp. 28-30, defines a positive dependent
t-literal as satisfied only when its operand values are defined and satisfy its
relation. It then defines `not l` as satisfied exactly when `l` is not
satisfied, and defines the reduct by retaining rules whose default-negated body
literals are satisfied. Balduccini 2013 section 2, pp. 550-551, repeats those
satisfaction and reduct clauses. The historical [Clingo{f}
documentation](https://mbal.asklab.net/clingof/) demonstrates the default idiom
`p #= 1 :- not p #!= 1` and an application/application default-negated
inequality.

These sources establish the implementation rule:

```text
positive L satisfied    => not L is false
positive L unsatisfied  => not L is true
```

Undefinedness is not a third truth value exposed to the source program. It is
a reason the positive dependent n-atom is not satisfied. No operator may be
replaced by its apparent complement.

## Truth tables

Here, `D/T` means both operands are defined and the positive relation is true;
`D/F` means both are defined and the relation is false. For scalar comparisons,
the right operand is syntactically ground and therefore cannot be undefined.

### Equality: `left #= right`

| Operand state | Positive equality | Default-negated equality |
| --- | --- | --- |
| D/T (defined and equal) | true | false |
| D/F (defined and different) | false | true |
| left undefined | false | true |
| right undefined (application operand) | false | true |
| both undefined (application operands) | false | true |

### Inequality: `left #!= right`

| Operand state | Positive inequality | Default-negated inequality |
| --- | --- | --- |
| D/T (defined and different) | true | false |
| D/F (defined and equal) | false | true |
| left undefined | false | true |
| right undefined (application operand) | false | true |
| both undefined (application operands) | false | true |

Thus `not f(a) #!= 1` is true both when `f(a)` is defined as `1` and when it is
undefined. Rewriting it to `f(a) #= 1` would lose the undefined case.

### Ordered relations: `#<`, `#<=`, `#>`, and `#>=`

ASPf-next retains its integer-only ordered-comparison boundary. A positive
ordered comparison is satisfied only when both runtime operands are defined
integers and the selected arithmetic relation holds.

| Operand state | Positive order | Default-negated order |
| --- | --- | --- |
| both integers, relation true | true | false |
| both integers, relation false | false | true |
| left undefined | false | true |
| right undefined (application operand) | false | true |
| both undefined (application operands) | false | true |
| left noninteger | false | true |
| right noninteger (application operand) | false | true |
| both noninteger | false | true |

The table applies independently to `<`, `<=`, `>`, and `>=`, including
negative integers, zero, and equality boundaries. Clingo's generic term order
must not be used.

## Accepted grammar and IR

The parser accepts exactly one `not` immediately before a complete body n-atom
whose positive form is already supported:

```text
body-n-atom := ["not"] application operator operand
operator    := "#=" | "#!=" | "#<" | "#<=" | "#>" | "#>="
operand     := supported-scalar | declared-application
```

`BodyComparison.negated: bool` records polarity explicitly. Its source span
covers `not` when present so lowering replaces the complete literal. Seed
assignments have no negation field. A negated assignment or any n-atom in a
rule head remains invalid.

Double default negation, aggregates, choices, conditional literals,
arithmetic, non-Herbrand variables, scalar value variables, and variables that
lack an independent ordinary positive body domain remain unsupported with
location-aware diagnostics.

## Reference lowering

Each default-negated comparison is lowered by defining a fresh private atom for
the satisfaction of its positive form and default-negating that atom:

```asp
% source
p(A) :- account(A), not balance(A) #>= 1000.

% conceptual reference translation
__aspf_sat_0(A) :-
    __aspf_value(balance(A),V),
    __aspf_integer(V),
    V >= 1000.
p(A) :- account(A), not __aspf_sat_0(A).
```

The helper body is exactly the existing positive-comparison lowering. Failed
definedness lookup, failed integer typing, or a false relation leaves the
helper absent; ordinary Clingo default negation then implements the historical
truth table directly.

Helpers are allocated by a lowering-local deterministic allocator. Every
negated comparison receives an independent identity in program order. The
predicate arguments are the unique ordinary source variables occurring in
either operand, ordered by their first source position. Consequently helper
instances cannot merge `A` with another `A`, `(A,B)` with another pair, or two
different comparisons. The reserved `__aspf_` prefix prevents source
collisions.

The frontend validates source safety before helpers exist. A generated positive
lookup may make the backend rule safe for Clingo, but it can never make an
invalid source variable acceptable. Unrelated ordinary body conditions are not
copied into helper definitions.

## Reduct and recursion review

For every supported ground comparison `L`, the fresh helper atom `sat_L` is
derivable exactly when the relational reference encoding satisfies positive
`L`. Replacing `not L` with `not sat_L` therefore makes the translated rule
survive the Clingo reduct exactly when the ASP{f} rule survives its historical
reduct test.

The helper is fresh, appears positively only in its defining head, and cannot
be named by source code. It is not an independent choice and introduces no
reverse implication. Dependencies from assignments through ordinary rules and
back through `not sat_L` remain default-negation cycles in the translated
program. Representative odd-loop, default-assignment, and multi-model cases
must remain executable regressions; this design does not claim equivalence for
syntax outside the supported fragment.

## Output boundary

Private satisfaction atoms begin with `__aspf_`. Existing model normalization
removes all such atoms from human and JSON model atoms, and they are never
reconstructed as assignments. `--emit-lowered` deliberately displays them as
part of the transparent reference translation.

## Non-goals

This design does not add global declaration mode, legacy visibility, historical
seed-equality safety, right-side value variables, non-Herbrand variables,
arithmetic, aggregates, choices, conditional literals, or a native backend.
