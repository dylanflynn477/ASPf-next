# Semantics notes

This milestone implements only the semantic commitments stated here. Historical
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

## Head assignments

An assignment fact lowers to an internal fact. A conditional head assignment
lowers to an internal rule head with the ordinary body preserved. No additional
causal, closed-world, inertia, or choice semantics is introduced.

## Positive body comparisons

`f(a) #= v` in a positive body lowers to the positive atom
`__aspf_value(f(a),v)`. It succeeds exactly when that value atom is true. If
`f(a)` is undefined or has another value, the body is false.

Default-negated comparisons are deferred because simply negating the internal
atom would conflate “undefined” and “defined with a different value” without an
explicit compatibility decision.

## Values and equality

Values are Clingo ground symbols in the restricted grammar: integers, symbolic
constants, or strings. Equality and inequality in the functionality constraint
therefore use Clingo's ground-symbol comparison. This milestone does not define
numeric coercion, arithmetic evaluation, or cross-type ASP{f} relations.

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
- ordinary atoms are sorted first and reconstructed assignments second for
  stable human output;
- unsupported ASP{f}-shaped syntax is rejected before Clingo receives it.

These should be compared with primary language specifications before a release
claims a named historical compatibility level.
