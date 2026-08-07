# Application operand semantics

Status: design contract for the typed-operands milestone.

This document records the clean-room semantic basis and the intentionally
restricted ASPf-next language accepted by this milestone. No historical
Clingo{f} source code was consulted.

## Primary-source basis

The following sources were inspected directly:

- Marcello Balduccini, [“A ‘Conservative’ Approach to Extending Answer Set
  Programming with Non-Herbrand Functions”](https://mbal.asklab.net/papers/bal12.pdf),
  2012 (B12), especially §2, printed pp. 26–28, and §3, pp. 28–29.
- Marcello Balduccini, [“ASP with non-Herbrand Partial Functions: a Language
  and System for Practical Use”](https://mbal.asklab.net/papers/bal13.pdf), 2013
  (B13), especially §2, journal pp. 548–551, and §3, p. 555.
- Marcello Balduccini and Michael Gelfond, [“Language ASP{f} with Arithmetic
  Expressions and Consistency-Restoring Rules”](https://mbal.asklab.net/papers/bg12.pdf),
  2012 author manuscript (BG12), especially §2, PDF pp. 3–4.
- Marcello Balduccini, [historical Clingo{f}
  documentation](https://mbal.asklab.net/clingof/) (CF), especially “Syntax” and
  “Syntax restrictions.”

B12 distinguishes seed t-atoms of the form `f = v`, where `v` is a constant,
from dependent t-atoms. Its examples include a dependent comparison between two
simple terms. B13 carries that distinction forward: rule heads contain seed
n-literals, while other operand/operator forms are dependent. B12 and B13 define
a dependent equality or inequality as satisfied only when both operands have
defined values and the values satisfy the relation. CF demonstrates
application-to-application equality concretely. BG12 explicitly includes all
six comparison operators and requires defined operand values interpreted by the
usual arithmetic relation.

This evidence supports dependent equality, inequality, and ordered comparison
between two simple non-Herbrand applications in a positive rule body. It does
not support treating application equality in a head as a copy assignment.

## Milestone grammar

The new accepted forms are:

```text
body-comparison ::= application operator application
operator        ::= #= | #!= | #< | #<= | #> | #>=
application     ::= declared-name
                  | declared-name "(" supported-argument-list ")"
```

The comparison must be one complete, positive rule-body literal. Both
application symbols must be explicitly declared with `#nherb`, have the declared
arity, and use the existing argument subset: ground supported terms or direct
ordinary variables. A scalar right operand continues to use the pre-existing
restricted grammar. A bare declared zero-arity name on the right denotes an
application; an undeclared bare symbolic constant remains a scalar.

Application/application comparisons in heads, default negation, aggregates,
choices, conditional literals, and arithmetic expressions remain unsupported.
So do right-side scalar variables, nested variables, and `_V` non-Herbrand
variables.

## Assignment versus dependent comparison

These are different IR and language concepts:

```asp
actual(a) #= 10.                         % scalar assignment
same(a) :- actual(a) #= expected(a).     % dependent comparison
```

An assignment has one application target and one ground scalar value. It may be
a fact or the sole rule head. A body comparison has an application left operand,
an application or scalar right operand, and an operator. Application equality is
body-only. In particular, `actual(a) #= expected(a).` is rejected and never
copies `expected(a)` into `actual(a)`.

The IR therefore uses typed `ScalarOperand` and `ApplicationOperand` values and
separate `Assignment` and `BodyComparison` nodes. This is enough structure for
the current semantics without introducing an unimplemented generic expression
tree.

## Definedness and comparison tables

Application equality and inequality require two successful value lookups:

| Left | Right | `#=` | `#!=` |
| --- | --- | --- | --- |
| defined `v` | defined `v` | true | false |
| defined `v1` | defined `v2`, `v1 != v2` | false | true |
| undefined | defined | false | false |
| defined | undefined | false | false |
| undefined | undefined | false | false |

Undefined is absence of an internal value fact; it is not a special value and
does not make positive inequality true. Inequality must not be implemented as
negation-as-failure of equality.

Ordered comparisons have this table:

| Left | Right | Result |
| --- | --- | --- |
| defined integer | defined integer | usual integer relation |
| undefined | any | false |
| any | undefined | false |
| defined non-integer | any | false |
| any | defined non-integer | false |

All four order operators use this rule. The source language discussed by BG12
has broader numerical expressions, but ASPf-next deliberately retains its
current integer-only boundary. Both runtime values are checked with the private
integer marker so Clingo's general symbol/string/term ordering cannot leak into
the result.

Equality and inequality accept every currently supported scalar value kind:
integer, symbolic constant, and string. There is no coercion between kinds.

## Reference lowering

For equality, a shared temporary gives the most direct encoding:

```asp
same(A) :- account(A),
    __aspf_value(actual(A),_AspfCmp0),
    __aspf_value(expected(A),_AspfCmp0).
```

Inequality uses two defined-value lookups:

```asp
different(A) :- account(A),
    __aspf_value(actual(A),_AspfCmp0),
    __aspf_value(expected(A),_AspfCmp1),
    _AspfCmp0 != _AspfCmp1.
```

Ordering adds an integer marker for each value before the arithmetic relation.
Generated variables come from a fresh allocator for each containing statement.
The allocator is deterministic and skips every identifier already present in
that statement. It has no module-global state.

## Variable safety

This milestone preserves the existing conservative source rule. Every ordinary
variable in either application key must occur independently in an ordinary,
unnegated, positive symbolic body literal in the same rule:

```asp
same(A) :- account(A), actual(A) #= expected(A).       % accepted
pair(A,B) :- account(A), account(B), actual(A) #= expected(B). % accepted
same(A) :- actual(A) #= expected(A).                   % rejected
```

The generated private lookups do not establish source safety, and one
non-Herbrand application cannot make another application's variables safe. This
is narrower than historical seed-equality safety and matches the prior
ASPf-next variable milestone.

## Compatibility boundary

This milestone implements only comparisons of simple declared applications and
the existing scalar subset. Historical ASP{f} permits broader terms, arithmetic,
aggregates, non-Herbrand variables, and safety behavior. Those features remain
deferred. The relational lowering is a correctness-oriented reference backend;
it makes no claim to reproduce historical Clingo{f}'s grounding efficiency or
solver integration.
