# Default-negated n-atoms

Status: semantics established; reference lowering intentionally deferred from
`historical-compatibility-1`.

## Primary-source semantics

B12 section 3 and B13 section 2 define an extended literal `not l` as satisfied
exactly when positive literal `l` is not satisfied. A positive dependent
n-atom is satisfied only when both values are defined and the relation holds.
Consequently, undefinedness is part of the truth table.

### Equality

| Value of `f(a)` | `f(a) #= 1` | `not f(a) #= 1` |
| --- | --- | --- |
| `1` | true | false |
| defined, not `1` | false | true |
| undefined | false | true |

### Inequality

| Value of `f(a)` | `f(a) #!= 1` | `not f(a) #!= 1` |
| --- | --- | --- |
| `1` | false | true |
| defined, not `1` | true | false |
| undefined | false | true |

### Ordered comparison

For `not f(a) #< 1`, default negation is false only when `f(a)` is defined with
a numerical value smaller than `1`. It is true for a defined value that does
not satisfy `<`, for undefinedness, and under the full historical language for
other cases where the positive comparison is not satisfied.

Thus `not (f(a) #!= 1)` cannot be rewritten as `f(a) #= 1`: both are true for
defined value `1`, but only the default-negated inequality is true when `f(a)`
is undefined.

## Lowering considerations

Default-negated scalar equality could be represented by negating one exact
lookup. Inequality, ordering, and application/application comparisons negate a
conjunction of definedness and relation checks, not a single atom. A faithful,
safe lowering therefore needs named auxiliary predicates (or an equivalent
structured transformation), deterministic freshness, variables copied with
their domains, and tests for every undefined side.

Introducing only the easy equality case would create an irregular language and
would not cover the historical default idiom `f #= v :- not f #!= v`.

## Decision

Keep all default-negated n-atoms unsupported in this branch. Strict historical
xfails cover equality with a different defined value and inequality with an
undefined application. Compatibility-2 may add one coherent transformation for
all six operators after the auxiliary-predicate safety design is reviewed.
