# Semantics notes

The current frontend implements only the semantic commitments stated here. Historical
ASP{f} behavior outside this list must not be inferred from the implementation.

## Partial functions

A supported ground non-Herbrand application is represented by a ground key such
as `balance(account1)`. A true internal atom:

```asp
__aspf_value(balance(account1),500)
```

means that the key's value is `500` in that answer set. If no internal value atom
exists for a key, the function application is undefined. Declarations do not
create values and there is no totality rule.

## Functionality

The reference backend adds:

```asp
:- __aspf_value(K,V1), __aspf_value(K,V2), V1 != V2.
```

Consequently, two different values for the same ground key make the program
unsatisfiable. Repeating the same value is harmless under ordinary ASP set
semantics.

Functionality is global across declared function names because the key includes
the complete application term. Thus `left(a)` and `right(a)` are distinct keys.

## Domain-safe source variables and grounding

An ordinary uppercase variable may occur as one complete application argument
only when an ordinary, unnegated positive symbolic body atom in the same rule
also contains that variable. For example:

```asp
low(A) :- account(A), balance(A) #< 1000.
```

The ordinary `account(A)` atom supplies the source grounding domain. Lowering
retains `A` in the key, so Clingo produces ground lookups such as
`__aspf_value(balance(checking),V)` only for the ordinary rule instances.
Grounding a variable key does not define it and does not add a totality rule.

Source safety is deliberately checked before lowering. A generated private
lookup or comparison variable cannot make a source variable safe, nor can
another n-atom, ordinary equality, negation, or a classically negated atom. A
scalar right operand remains ground. A declared right application may use the
same direct argument subset, but every variable there also needs an independent
ordinary domain occurrence. This is a conservative compatibility subset, not a
claim that historical equality-provided safety or non-Herbrand variables have
been implemented.

## Head assignments

An assignment fact lowers to an internal fact. A conditional head assignment
lowers to an internal rule head with the ordinary body preserved. No additional
causal, closed-world, inertia, or choice semantics is introduced.

## Positive body comparisons

`f(a) #= v` in a positive body lowers to the positive atom
`__aspf_value(f(a),v)`. It succeeds exactly when that value atom is true. If
`f(a)` is undefined or has another value, the body is false.

`f(a) #!= v` first looks up a defined value and then compares it with `v`. It is
false when `f(a)` is undefined, rather than treating absence of equality as
inequality.

`f(a) #< n`, `#<=`, `#>`, and `#>=` require a defined integer value and an
integer literal `n`. The reference backend tags integer assignment literals with
`__aspf_integer/1`; an ordered body requires both that tag and the value lookup.
Undefined, symbolic, and string values therefore make the ordered comparison
false. No coercion or general Clingo term ordering is exposed as numeric
semantics.

For `f(a) #= g(a)` and `f(a) #!= g(a)`, both declared applications are looked
up. Equality shares one generated value variable; inequality retrieves two and
compares them explicitly. Thus either undefined operand makes both literals
false. Application equality is body-only and does not copy a value in a rule
head.

Ordered application comparison retrieves both values and requires an integer
marker for each before applying the arithmetic relation. This preserves the
same integer-only boundary and prevents Clingo term ordering on either side.

Default-negated comparisons are deferred because simply negating the internal
atom would conflate “undefined” and “defined with a different value” without an
explicit compatibility decision.

## Values and equality

Values are Clingo ground symbols in the restricted grammar: integers, symbolic
constants, or strings. Equality and inequality in the functionality constraint
therefore use Clingo's ground-symbol comparison. Ordered comparisons are
integer-only as described above. The frontend does not define numeric coercion,
arithmetic evaluation, or cross-type ASP{f} relations.

## Ordinary ASP and `#show`

Ordinary statements are handed to Clingo. Ordinary `#show` directives determine
the ordinary portion of normalized output. The renderer separately reads all
true atoms to recover `__aspf_value/2`, so an assignment remains visible in
ASP{f} notation when ordinary output is restricted.

## Decisions needing broader compatibility review

The following current choices are conservative implementation policy, not claims
about every historical ASP{f} version:

- same-name/same-arity declarations may repeat;
- declarations are visible across all CLI input files and may follow uses;
- zero-arity functions normalize to a bare key such as `mode`;
- ordinary recursively ground compound terms are accepted as application
  arguments, but not as values;
- ordinary variables are accepted only as direct key arguments with an
  independent positive symbolic body domain;
- ordinary atoms are sorted first and reconstructed assignments second for
  stable human output;
- unsupported ASP{f}-shaped syntax is rejected before Clingo receives it.

These should be compared with primary language specifications before a release
claims a named historical compatibility level.
