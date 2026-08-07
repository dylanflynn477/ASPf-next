# Variable semantics research

Status: architecture research, not an implemented language commitment.

This document records the primary-source basis for a future variable milestone in
ASPf-next. It separates historical ASP{f}, historical Clingo{f}, current Clingo behavior,
and possible ASPf-next restrictions. No historical implementation source code was
consulted, and no production behavior follows from this document by itself.

## Executive conclusion

Historical ASP{f}/Clingo{f} has two materially different variable mechanisms:

1. **ordinary (Herbrand/traditional) variables**, which are replaced during grounding;
2. **non-Herbrand variables (n-variables)**, written with a leading underscore in
   Clingo{f}, which are deliberately treated as ground by the grounder and receive values
   later through defining equality n-atoms.

They must not be represented by one undifferentiated `Variable` node. In particular,
turning an n-variable into a modern Clingo variable would erase the historical distinction
and the grounding-size motivation for the feature.

The primary sources also distinguish seed equality from dependent comparisons. A positive
seed `#=` body literal can provide safe occurrences for ordinary variables in historical
Clingo{f}. Application-to-application equality, `#!=`, `#<`, `#<=`, `#>`, and `#>=` are
dependent n-atoms: variables occurring only there are unsafe. Every positive dependent
comparison is false if either operand is undefined.

The current reference backend can correctly support a narrower subset: ordinary variables
used directly as arguments of declared applications, provided every such variable is
independently domain-safe in an ordinary positive body atom. It cannot faithfully implement
n-variables without new value-binding machinery.

## Source key and evidence policy

The following primary sources were consulted directly:

- **B12** — Marcello Balduccini, [“A ‘Conservative’ Approach to Extending Answer Set
  Programming with Non-Herbrand Functions”](https://mbal.asklab.net/papers/bal12.pdf),
  2012, DOI
  [10.1007/978-3-642-30743-0_3](https://doi.org/10.1007/978-3-642-30743-0_3).
  Relevant locations: §2, printed pp. 26–28; §3, printed pp. 28–29; §4, printed
  pp. 32–33.
- **B13** — Marcello Balduccini, [“ASP with non-Herbrand Partial Functions: a Language
  and System for Practical Use”](https://mbal.asklab.net/papers/bal13.pdf), 2013,
  DOI [10.1017/S1471068413000343](https://doi.org/10.1017/S1471068413000343).
  Relevant locations: §2, journal pp. 548–551; §3, journal pp. 551–555.
- **BG12** — Marcello Balduccini and Michael Gelfond, [“Language ASP{f} with Arithmetic
  Expressions and Consistency-Restoring Rules”](https://mbal.asklab.net/papers/bg12.pdf),
  2012 author manuscript, also available as
  [arXiv:1301.1387](https://arxiv.org/abs/1301.1387). Relevant locations: §2, PDF
  pp. 3–4.
- **CF** — Marcello Balduccini, [historical Clingo{f} documentation](https://mbal.asklab.net/clingof/),
  especially “Syntax,” “Syntax restrictions,” and examples P1–P5.
- **CLINGO** — Potassco, [current Clingo input-language guide](https://potassco.org/guide/language/),
  especially “Safety of Variables,” and the official
  [Clingo 5.8 `Control` API](https://potassco.org/clingo/python-api/5.8/clingo/control.html).

The papers define a language, while CF documents one historical concrete implementation.
Where those accounts differ or leave an implementation detail implicit, this document keeps
the distinction visible rather than treating one as a correction of the other.

## Terminology

### Term and n-atom vocabulary

B12 §2, pp. 26–27 defines functional terms and term-atoms (t-atoms). B13 §2,
pp. 548–549 generalizes the vocabulary to simple, arithmetic, and aggregate terms and calls
their comparisons n-atoms. Historical Clingo{f} prefixes the six comparison connectives with
`#`.

A **seed n-atom** has equality form `f #= v`, where `f` is a simple non-Herbrand term and
`v` is a constant. It can appear as a rule head and asserts a supported value. An n-atom that
is not a seed n-atom is **dependent**. In particular, application-to-application equality,
inequality, and ordered comparisons are dependent. B13 §2, pp. 549–550 and BG12 §2,
PDF pp. 3–4 provide these classifications and their ground satisfaction conditions.

ASPf-next currently calls an occurrence such as `balance(a) #= 500` an assignment in a head
and a positive comparison in a body. The historical seed/dependent distinction remains
important for variable safety even though the current IR does not encode it explicitly.

### Ordinary variables

Ordinary variables are the variables used by the host ASP language. B12 §2, p. 28 says that
variables may replace constants and terms, and defines a non-ground rule through its ground
instances. Its abstract grounding substitutes elements of `C ∪ T`. B13 §2, p. 550 gives a
later account in which ordinary variables are replaced by appropriately sorted constants and
arithmetic over numerical constants is evaluated.

In historical Clingo{f}, ordinary variables follow the host Clingo grounding model. B13 §3,
pp. 552–553 says that Clingo{f} grounding follows Clingo and retains its domain-predicate
requirements. Ordinary variables can occur:

- in regular atoms and rule heads under the host language’s normal safety rules;
- as arguments of non-Herbrand applications inside n-atoms;
- as constant/value positions in seed equalities;
- in dependent n-atoms only when made safe elsewhere;
- in arithmetic and aggregate expressions in the broader historical language.

The last two categories are wider than any currently implemented ASPf-next feature.

### Non-Herbrand variables

B13 §3, pp. 552–553 introduces a second kind of variable for Clingo{f}. The concrete spelling
is an alphanumeric identifier prefixed by `_`, with examples such as `_v` and `_x12`. These
are called **n-variables**. The paper’s key operational statement is that n-variables are
“considered ground expressions” and are therefore not substituted by the grounder.

N-variables are value placeholders handled after ordinary grounding. They exist to avoid
grounding a rule once for every possible value of a non-Herbrand application. They are not
anonymous variables and are not merely an alternate spelling of ordinary Clingo variables.

For a ground rule, an equality `ν #= t` or `t #= ν` defines n-variable `ν`. B13 then defines
an index assignment and requires every rule containing n-variables to be **n-stratified**:
each n-variable must have a positive defining equality whose right-hand term has a strictly
lower index. The paper imposes two explicit restrictions:

1. n-variables cannot occur as arguments of simple terms or aggregate terms;
2. every rule containing them must be n-stratified.

Thus `_V` cannot be accepted as an argument in `balance(_V)`. A future frontend must also
distinguish `_V` from modern Clingo’s underscore-prefixed variable syntax before handing any
lowered program to Clingo.

## Historical grammar relevant to variables

The abstract grammar below summarizes B12 §2, B13 §2, and BG12 §2. It is descriptive, not a
proposal for immediate implementation.

```text
simple-term       ::= function-symbol "(" constant-or-variable-list ")"
                    | zero-arity-function-symbol
arithmetic-term   ::= simple-term | numeric-expression
aggregate-term    ::= historical aggregate expression
term              ::= simple-term | arithmetic-term | aggregate-term

n-atom            ::= term op term
op                ::= #= | #!= | #< | #<= | #> | #>=
seed-n-atom       ::= simple-term #= constant
dependent-n-atom  ::= n-atom other than seed-n-atom

ordinary-variable ::= host-Clingo variable
n-variable         ::= "_" alphanumeric-name
```

For non-ground source, whether an equality becomes a seed n-atom is understood through its
ground instances. CF’s accepted P1 example, `p(X,Y) :- l(X) #= Y.`, is the most direct
evidence that its positive equality supplies safe ordinary-variable occurrences.

## Ordinary-variable safety

### Historical rule

CF states: “Variables occurring in dependent t-literals must satisfy the same safety
requirements as those occurring in literals under default negation.” Its P1–P5 examples make
the rule operational:

```asp
% CF P1: accepted
p(X,Y) :- l(X) #= Y.

% CF P3: accepted
d(a;b).
l(a) #= 3.
p(X) :- d(X), l(X) #!= 2.

% CF P4: rejected
l(a) #= 3.
p(X) :- l(X) #!= 2.

% CF P5: rejected
l(a) #= 3.
p(X,Y) :- l(X) #!= Y.
```

The evidence supports these conclusions:

- a positive seed `#=` literal may provide safe occurrences for ordinary variables;
- `#!=` does not provide safe occurrences;
- variables in `#!=` must be made safe by another positive domain literal such as `d(X)`;
- the same dependent-literal rule applies to application-to-application equality and ordered
  comparisons because they are dependent n-atoms under B13/BG12.

This is a grounding-safety relation, not Prolog-style procedural binding. B12 and B13 define
the meaning of a non-ground program through its ground instances. Saying that equality
“binds” a variable means that historical Clingo{f} accepts the occurrence as a source of its
grounding domain.

### Safety by operator

| Source form | Historical class | Can supply ordinary-variable safety? | Undefined operand |
| --- | --- | --- | --- |
| `f(X) #= Y` where ground instances are seed assignments | seed equality | Yes, as demonstrated by CF P1 | body literal is false when no matching assignment exists |
| `f(X) #= g(Y)` | dependent equality | No; variables need safe occurrences elsewhere | false if either application is undefined |
| `f(X) #!= t` | dependent inequality | No | false if either operand is undefined |
| `f(X) #< t` | dependent ordered comparison | No | false if either operand is undefined |
| `f(X) #<= t` | dependent ordered comparison | No | false if either operand is undefined |
| `f(X) #> t` | dependent ordered comparison | No | false if either operand is undefined |
| `f(X) #>= t` | dependent ordered comparison | No | false if either operand is undefined |
| `not L`, for any n-atom `L` | default-negated literal | No | true when positive `L` is not satisfied, including relevant undefined cases |

A variable in a rule head must still be made safe by its body. Nothing in the sources supports
treating a head assignment as a domain generator for its own variables.

### Equality can bind, but only in the historical safety sense

The answer to “can equality bind a previously unbound variable?” is **yes, with
qualification**. CF P1 accepts both `X` and `Y` when their only body occurrences are in
`l(X) #= Y`. That establishes historical Clingo{f} safety behavior for positive seed equality.
It does not establish:

- procedural unification;
- support for binding through dependent application equality;
- permission for `#!=` or order comparisons to bind;
- permission for ASPf-next to let a generated private predicate silently define the source
  language’s safety relation.

The deliberately restricted milestone proposed separately does not initially reproduce this
equality-provided safety. It requires an ordinary positive domain atom for every variable used
inside an n-atom. This is a documented compatibility restriction.

## How function arguments are grounded

For ordinary variables, grounding substitutes members of the finite host-language domain.
B13 §3, pp. 552–553 says historical Clingo{f} uses Clingo’s grounding approach and normal
domain-predicate requirements. Therefore:

```asp
account(a;b).
low(A) :- account(A), balance(A) #< 1000.
```

has ground instances for the domain values supplied by `account/1`, including keys
`balance(a)` and `balance(b)`. The non-Herbrand value of each key is not needed to construct
the key term during grounding.

B12’s abstract account permits substitution by constants and terms, while B13’s later account
speaks in terms of constants of suitable sorts. Historical Clingo{f} also permits a traditional
variable to stand for a reified term outside an n-atom; B13 §3, p. 552 uses `is_weight(F),
F #< 0`. ASPf-next intentionally rejects declared non-Herbrand symbols outside supported
n-atom keys, so this reification pattern is not currently compatible and is not part of the
recommended milestone.

N-variables are different: the grounder does not substitute them. The solver-side Clingo{f}
machinery assigns their values from positive defining equality n-atoms after grounding. That
mechanism has no analogue in the current ASPf-next reference backend.

## Definedness and comparisons

B12 §3, pp. 28–29, B13 §2, pp. 550–551, and BG12 §2, PDF pp. 3–4 define a simple
term as undefined when no seed assignment gives it a value. A positive dependent n-atom is
satisfied only when both operands are defined and their values satisfy the comparison.

Consequences for all variable designs:

- `balance(A) #!= 1000` is not negation-as-failure of equality;
- an undefined `balance(A)` makes `#!=` false, not true;
- ordered comparisons do not give undefined a numeric sentinel;
- equality between two undefined applications is false, not true;
- default-negated equality is a separate construct and can be true when equality is not
  satisfied because of undefinedness;
- adding a totality rule changes the language.

B13 §3, pp. 554–555 describes historical Clingo{f} propagation using an explicit undefined
state and confirms that body n-atoms are false if one or both assigned term values are
undefined. ASPf-next’s absence of `__aspf_value(K,V)` is a different representation of the
same restricted observable behavior.

## Prototype reference-lowering analysis

This section is a paper analysis, not production code. It assumes the existing global
functionality constraint and reserved internal namespace.

### Domain-safe ordered comparison

Source:

```asp
account(a).
account(b).

#nherb balance/1.

low(A) :-
    account(A),
    balance(A) #< 1000.
```

Candidate lowering:

```asp
low(A) :-
    account(A),
    __aspf_value(balance(A),V),
    __aspf_integer(V),
    V < 1000.
```

Analysis:

- `A` is safe independently through the positive ordinary atom `account(A)`.
- `balance(A)` is a Herbrand key term only inside the private relation. Constructing the key
  after substituting `A` does not evaluate the non-Herbrand application.
- generated `V` is safe in modern Clingo because it occurs in the positive symbolic literal
  `__aspf_value(balance(A),V)`.
- `__aspf_integer(V)` preserves the current numeric-only boundary; it prevents Clingo’s
  generic term ordering from being mistaken for ASP{f} arithmetic order.
- if `balance(a)` is undefined, no lookup atom exists and `low(a)` is not derived.
- the translation agrees with the historical dependent-comparison definedness rule for this
  domain-safe, ground-right-operand subset.

This translation is therefore suitable for the restricted milestone.

### Application-to-application equality

Source:

```asp
same(A) :-
    account(A),
    actual(A) #= expected(A).
```

Candidate lowering:

```asp
same(A) :-
    account(A),
    __aspf_value(actual(A),V),
    __aspf_value(expected(A),V).
```

The shared value variable makes the body true only if both applications are defined with the
same value. Functionality ensures that each key has at most one value. Modern Clingo regards
`A` and `V` as safe, and undefinedness is preserved by the two positive lookups.

This analysis suggests that the relational backend could represent this ground semantics, but
it is **not** a recommendation for the first variable milestone. Application-to-application
operands require a richer operand IR, declared-symbol validation on both sides, value-kind
rules, and additional conformance work. Current ASPf-next deliberately rejects this syntax.

### Historically unsafe inequality

Source:

```asp
different(A) :- balance(A) #!= 1000.
```

A mechanically plausible lowering is:

```asp
different(A) :-
    __aspf_value(balance(A),V),
    V != 1000.
```

Modern Clingo accepts this rule because the generated positive lookup provides safe
occurrences for both `A` and `V`. That is not enough. CF P4 classifies the analogous source
rule as unsafe: a dependent inequality cannot provide the source variable’s domain.

The frontend must reject the source rule before lowering. The private lookup may bind a fresh
backend variable such as `V`; it must not retroactively make source variable `A` safe.

### Domain-safe inequality

Adding an independent domain atom resolves the historical safety problem:

```asp
different(A) :-
    account(A),
    balance(A) #!= 1000.
```

```asp
different(A) :-
    account(A),
    __aspf_value(balance(A),V),
    V != 1000.
```

Undefined values remain false because the positive lookup fails. This form is suitable for the
restricted milestone.

## Modern Clingo behavior probes

These are **Clingo 5.8.1 behavior experiments, not ASP{f} conformance tests**. They were run
through the official Python API by adding each ordinary program to `clingo.Control`, grounding,
and solving.

| Probe | Clingo 5.8.1 result | Design consequence |
| --- | --- | --- |
| domain-safe ordered lowering with `account(A)` | grounds; derives only the defined qualifying key | candidate lowering is viable |
| inequality lowering without `account(A)` | grounds and derives `different(a)` from the private lookup | frontend must enforce source-level dependent-literal safety |
| shared-value application equality | grounds; derives equality only for two defined equal values | relational encoding is plausible but deferred |
| `1000 < active` and `1000 < "500"` | grounds and evaluates using Clingo term order | raw Clingo ordering is not numeric ASP{f} ordering |
| `different(A) :- V != 1000.` | rejected as unsafe | a comparison alone does not make modern Clingo variables safe |

Current Clingo’s documented safety rules say that positive symbolic literals provide safe
occurrences, while acyclic assignments or two-sided integer bounds can also make variables safe.
The proposed first milestone intentionally recognizes only direct occurrences in ordinary
positive symbolic domain atoms. It does not adopt every modern Clingo safety inference as an
ASPf-next language rule.

## What the current backend can reproduce

The relational backend is sufficient for the following restricted behaviors:

- ordinary variables in direct application-argument positions;
- those variables independently bounded by ordinary positive body atoms;
- ground right operands from the already supported value classes;
- head assignments whose argument variables are independently body-safe;
- positive body `#=`, `#!=`, and numeric order comparisons with that key shape;
- partiality through absent `__aspf_value/2` atoms;
- functionality through the existing global integrity constraint;
- stable model reconstruction after grounding.

The backend can also express some broader ground relations, such as shared-value
application-to-application equality, but frontend and IR work must precede any such acceptance.

## What requires more architecture

### Preprocessing and explicit source-level safety

Even the restricted milestone needs a frontend safety pass. Delegating all safety to Clingo is
incorrect because generated private lookups can make historically unsafe dependent comparisons
look safe. The pass must distinguish source variables from generated variables and ordinary
domain atoms from n-atoms.

### Explicit finite value domains

Ordinary variables in value positions could be compiled to relational lookups or explicit
finite domains. Doing so can reproduce some ground semantics but can also change which
constants are considered and create large groundings. Equality-provided safety should be a
separate milestone with an explicit domain model and conformance evidence.

### Theory atoms or a native propagator

N-variables require solver-time value placeholders, defining equalities, n-stratification, and
undefined-value propagation. A custom theory/propagator backend is the natural candidate for
preserving their purpose. Treating them as ordinary variables plus a finite domain is at best a
separately specified compatibility backend and does not preserve their historical grounding
behavior.

Arithmetic over non-Herbrand values, aggregates containing n-atoms, and solver-side value
propagation likewise remain native-backend research topics.

## Tempting transformations that are wrong

### Treating absence as inequality

```asp
% Wrong
different(A) :- account(A), not __aspf_value(balance(A),1000).
```

This derives `different(A)` when `balance(A)` is undefined. Historical positive `#!=` requires
defined, unequal operands.

### Letting a private lookup legalize a source variable

```asp
% Plausible Clingo, historically unsafe source
different(A) :- __aspf_value(balance(A),V), V != 1000.
```

Modern Clingo safety is satisfied, but CF P4 says the source dependent inequality cannot bind
`A`. Source safety must be checked before introducing private literals.

### Using generic Clingo term ordering

```asp
% Wrong for numeric ASP{f} order
low(A) :- account(A), __aspf_value(balance(A),V), V < 1000.
```

Without a numeric guard, Clingo compares numbers, symbolic constants, strings, and compound
terms using its generic term order. ASP{f} ordered arithmetic cannot be delegated to that order.

### Comparing key syntax instead of values

```asp
% Wrong
same(A) :- account(A), actual(A) = expected(A).
```

This compares two different Herbrand key terms and never consults their partial values.

### Silently totalizing a partial function

Generating one value for every grounded key, or a distinguished ordinary `undefined` value,
changes partiality and can make comparisons true that historical ASP{f} makes false.

### Turning every variable into an unrestricted Clingo variable

This loses both the safety distinction for dependent n-atoms and the grounder-inert semantics
of n-variables. It can also multiply the grounding over an unintended Herbrand universe.

### Treating equality as unrestricted procedural unification

CF P1 establishes a safety behavior for positive seed equality. It does not justify binding
through application equality, negated equality, arithmetic equality, or equality in arbitrary
nested contexts.

### Enumerating an inferred global value domain

Adding `value(V)` from every constant visible in the program can introduce unintended
candidate values, make grounding depend on unrelated files, and obscure the distinction
between a function being undefined and merely not equal to one enumerated constant.

### Flattening n-variables into ordinary variables

Replacing `_v` with `V` forces grounding over values and defeats the feature’s historical
purpose. It also ignores defining equalities and n-stratification.

## Historical ASP{f} versus ASPf-next

| Area | Historical language/system | Current ASPf-next architecture |
| --- | --- | --- |
| ordinary variables | supported broadly through grounding | rejected inside n-atoms |
| seed equality safety | may provide safe variable occurrences | no source-variable safety model yet |
| dependent comparison safety | variables must be safe elsewhere | all variables rejected, so safely narrower |
| n-variables | grounder-inert, equality-defined, n-stratified | no representation or backend mechanism |
| declared names outside n-atoms | treated as ordinary Herbrand terms in Clingo{f} | rejected to prevent semantic leakage |
| application-to-application comparison | supported | rejected |
| arithmetic/aggregates | supported in broader language | rejected |
| partiality | explicit semantic undefinedness | absence of a private value atom |
| grounding backend | modified historical Clingo{f} | unmodified modern Clingo through Python API |

## Open semantic and compatibility questions

These questions should remain explicit rather than being answered by implementation accident:

1. B12’s abstract grounding ranges over constants and terms, whereas B13’s later presentation
   describes constants of suitable sorts and Clingo-style domains. Which compatibility target
   should govern equality-provided safety in ASPf-next?
2. What exact lexical forms should count as historical n-variables, especially `_`, `_X`, and
   case variants, without conflicting with modern Clingo variable syntax?
3. Should a future equality milestone reproduce CF P1 by deriving a finite domain from private
   assignment heads, require an explicit user domain, or defer to a native backend?
4. Can multiple positive seed equalities safely provide mutually dependent ordinary-variable
   domains, and what cycle rule should the frontend enforce?
5. Should classically negated ordinary atoms count as domain providers in the first milestone?
   Modern Clingo can make variables safe there, but a narrower unnegated-only rule is easier to
   diagnose and specify.
6. How should source-level safety interact with ordinary Clingo acyclic assignments and bounded
   comparisons? The proposed first milestone deliberately does not treat them as domain atoms.
7. What finite-domain assumptions are needed to prevent accidental grounding growth from
   recursive ordinary Herbrand terms?
8. Can application-to-application equality share one value variable for all historical value
   classes once compound values and variable values are introduced?
9. How should n-variable undefinedness and multiple defining equalities be represented in a
   future theory/propagator interface?
10. Does the historical Clingo{f} implementation impose additional safety restrictions in
    aggregates, choices, or conditional literals beyond the public documentation? Those
    constructs should remain unsupported until primary-source evidence is sufficient.

## Recommendation

**GO WITH CONDITIONS** — implement only ordinary, explicitly domain-safe variables in direct
non-Herbrand application arguments. Require each such variable to occur directly in an
ordinary, unnegated, positive symbolic body atom in the same rule. Keep every right operand
ground, keep n-variables rejected, and do not allow a generated private lookup or another
n-atom to establish source safety.

Under those conditions, the current reference backend is sufficient. The exact proposed
language and implementation work are specified in
[`variable-milestone-plan.md`](variable-milestone-plan.md).
