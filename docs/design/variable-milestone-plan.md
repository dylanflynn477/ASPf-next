# Restricted ordinary-variable milestone plan

Status: implemented as an unreleased development increment. This document
records the design contract used by the implementation.

## Decision

**GO WITH CONDITIONS.** The implementation adds ordinary variables only in
direct argument positions of declared non-Herbrand applications, and only when every such
variable has an independent domain occurrence in an ordinary positive body atom in the same
rule.

This is intentionally narrower than historical ASP{f}/Clingo{f}. It does not implement
historical equality-provided safety, non-Herbrand variables, variables in value operands, or
application-to-application comparisons. The restriction is justified in
[`variable-semantics.md`](variable-semantics.md).

## User-visible goal

Accept programs such as:

```asp
account(a).
account(b).

#nherb balance/1.

balance(a) #= 500.
low(A) :-
    account(A),
    balance(A) #< 1000.
```

The result contains `low(a)` and no assignment or `low/1` atom for `b`. Undefinedness is
unchanged: the domain fact `account(b)` creates a candidate key but does not define its value.

Also accept domain-safe assignment heads:

```asp
#nherb status/1.
person(alice;bob).
status(P) #= active :- person(P).
```

Do not accept the following merely because a generated private lookup would make modern
Clingo consider it safe:

```asp
#nherb balance/1.
different(A) :- balance(A) #!= 1000.
```

## Exact grammar

The milestone extends only the application arguments in syntax already supported by
ASPf-next.

```text
ordinary-variable ::= UPPER (ALNUM | "_")*
UPPER             ::= "A" | ... | "Z"

variable-argument ::= ordinary-variable
key-argument      ::= existing-ground-argument | variable-argument

declared-key      ::= declared-zero-arity-name
                    | declared-name "(" key-argument ("," key-argument)* ")"

ground-value      ::= existing integer | symbolic constant | string value
integer-value     ::= existing integer literal

head-assignment   ::= declared-key "#=" ground-value

body-comparison   ::= declared-key "#="  ground-value
                    | declared-key "#!=" ground-value
                    | declared-key "#<"  integer-value
                    | declared-key "#<=" integer-value
                    | declared-key "#>"  integer-value
                    | declared-key "#>=" integer-value
```

Restrictions embedded in this grammar:

- a variable can replace one complete, top-level application argument;
- a variable cannot occur inside a compound argument such as `balance(owner(A))`;
- a variable cannot be the application/function name;
- the right operand remains ground;
- `_`, `_X`, `_v`, and every other underscore-prefixed form are outside this milestone;
- variable pools, intervals, arithmetic, tuples, and scripting terms inside n-atoms remain
  unsupported;
- existing placement restrictions for heads, bodies, aggregates, choices, conditional
  literals, disjunction, and default negation remain unchanged.

Ordinary ASP statements that contain no ASPf-next syntax retain normal modern Clingo variable
syntax and safety. The new restrictions apply only to variables used inside supported n-atoms.

## Exact source-level safety condition

For each rule containing a supported n-atom, let `NV(r)` be the set of ordinary variable names
occurring as direct arguments of the n-atom’s declared key.

Let `D(r)` be the set of variable names that occur directly or nested in an **ordinary domain
literal** in the same rule body. For this milestone, an ordinary domain literal is narrowly
defined as:

- a complete top-level body literal;
- an unnegated, positive symbolic atom;
- not an n-atom;
- not a comparison, arithmetic assignment, boolean literal, aggregate, theory atom,
  conditional literal, or choice/disjunctive element;
- not an occurrence of a declared non-Herbrand symbol or reserved `__aspf_` name.

The rule is accepted only if:

```text
NV(r) ⊆ D(r)
```

The occurrence order of body literals does not matter. A domain atom may appear before or
after the n-atom in source.

Examples:

```asp
% Safe: A occurs in the ordinary domain atom account(A).
low(A) :- account(A), balance(A) #< 1000.

% Safe: the same domain occurrence covers multiple n-atoms.
review(A) :- account(A), balance(A) #!= 0, score(A) #>= 50.

% Safe head assignment.
status(A) #= active :- account(A).

% Unsafe: dependent comparison cannot supply A's domain.
different(A) :- balance(A) #!= 1000.

% Unsafe in this restricted milestone: default negation is not a domain source.
low(A) :- not blocked(A), balance(A) #< 1000.

% Unsafe in this restricted milestone: ordinary comparison inference is not a domain source.
low(A) :- A = a, balance(A) #< 1000.

% Unsafe in this restricted milestone: another n-atom is not a domain source.
low(A) :- status(A) #= active, balance(A) #< 1000.
```

This rule is stricter than both historical seed-equality safety and modern Clingo’s full safety
analysis. That is deliberate. It makes source safety independent of generated backend atoms and
keeps the first implementation auditable.

After ASPf-next performs this check, modern Clingo remains responsible for validating the
complete lowered rule. The frontend check is an additional language boundary, not a replacement
for Clingo’s ordinary safety checker.

## Exact lowering

Variable names are retained when rendering the key. Existing collision-free private value
variables remain generated per rule.

### Head equality

```asp
balance(A) #= 0 :- account(A).
```

lowers to:

```asp
__aspf_value(balance(A),0) :- account(A).
```

Grounding over `account/1` produces one private value atom per domain member. The existing
functionality constraint still prevents two distinct values for the same grounded key.

### Positive body equality

```asp
zero(A) :- account(A), balance(A) #= 0.
```

lowers to:

```asp
zero(A) :- account(A), __aspf_value(balance(A),0).
```

The equality is false for undefined or differently valued keys.

### Positive body inequality

```asp
nonzero(A) :- account(A), balance(A) #!= 0.
```

lowers to an equivalent collision-free form:

```asp
nonzero(A) :-
    account(A),
    __aspf_value(balance(A),_AspfNeq0),
    _AspfNeq0 != 0.
```

The positive lookup preserves the rule that undefined is not unequal.

### Positive ordered comparison

```asp
low(A) :- account(A), balance(A) #< 1000.
```

lowers to an equivalent collision-free form:

```asp
low(A) :-
    account(A),
    __aspf_value(balance(A),_AspfCmp0),
    __aspf_integer(_AspfCmp0),
    _AspfCmp0 < 1000.
```

The same path applies to `#<=`, `#>`, and `#>=`. The integer marker remains required; raw
Clingo comparison would otherwise use generic term ordering for symbolic and string values.

### Grounding and undefinedness invariants

- A variable in a key affects which ground key terms are constructed; it does not define a
  value.
- Generated `_AspfNeqN` and `_AspfCmpN` variables are backend variables, not source
  n-variables.
- A domain atom does not totalize the function.
- Absence of `__aspf_value(key,value)` leaves the grounded key undefined.
- No value-domain rule is generated.
- The existing functionality constraint is unchanged.
- Model normalization continues to hide every `__aspf_` atom.

## Explicitly unsupported cases

The implementation task must retain location-aware rejection for all of the following:

### Variable kinds and positions

- non-Herbrand/n-variables such as `_V`, `_v`, and `_x12`;
- anonymous `_` in an n-atom;
- lowercase identifiers used as variables;
- variables as function/application names, for example `F #< 0`;
- variables on the right of any n-atom;
- variables nested in compound application arguments, for example `balance(owner(A))`;
- variables inside strings or comments remain inert, not rejected;
- variables in a zero-arity key are structurally impossible and must not alter zero-arity
  behavior.

### Safety sources not recognized yet

- a variable occurring only in a seed body equality, even though historical Clingo{f} accepts
  cases such as `p(X,Y) :- l(X) #= Y`;
- a variable occurring only in `#!=` or an ordered comparison;
- a variable made safe only by another n-atom;
- a variable made safe only by default-negated or classically negated atoms;
- a variable made safe only by ordinary equality, assignment, interval, or bounded comparison;
- local aggregate or conditional-literal variables;
- a variable whose only domain occurrence is in a head, choice, disjunction, aggregate, or
  theory atom.

### Existing language exclusions

- default-negated n-atoms;
- arithmetic inside n-atoms;
- application-to-application operands;
- n-atoms inside aggregates, choices, conditional literals, or disjunctive heads;
- ordered comparison heads;
- inequality heads;
- global `#nherb.` and legacy visibility directives;
- native propagator or theory-atom behavior;
- declared non-Herbrand symbols used as ordinary predicates or Herbrand terms.

## Parser and scanner changes

The implementation should remain scanner-based and location-aware; it must not use global
regex replacement.

1. Extend term tokenization to recognize an ordinary variable only when it occupies one
   complete direct application-argument span.
2. Preserve the variable’s exact source spelling and half-open source span.
3. Recognize underscore-prefixed tokens separately and reject them as unsupported
   non-Herbrand variables at their first character.
4. Split a rule body into top-level literals while respecting comments, strings, parentheses,
   brackets, braces, and multiline layout.
5. Classify ordinary positive symbolic body atoms conservatively. Do not count syntax that the
   classifier cannot prove is a domain atom.
6. Collect domain-providing variable names from those atoms.
7. After all supported n-atoms in the rule are parsed, validate each source variable against the
   collected domain set.
8. Keep the existing declared-symbol and reserved-namespace passes. Only the declared key name
   remains exempt; variable support must not widen that exemption.
9. Preserve ordinary Clingo statements byte-for-byte whenever they contain no supported ASP{f}
   syntax.

The source-safety pass should run before lowering so a private predicate can never legalize an
invalid source rule.

## IR changes

Use typed nodes; do not store a variable as a `GroundTerm`.

Recommended shape:

```python
@dataclass(frozen=True, slots=True)
class VariableTerm:
    name: str
    span: SourceSpan

KeyArgument = GroundTerm | VariableTerm
```

Equivalent concrete unions are acceptable. Required properties are:

- ground and variable arguments remain distinguishable without reparsing text;
- variable spans support precise diagnostics;
- `FunctionApplication` renders both argument kinds without changing ground rendering;
- n-variable syntax is not represented as an ordinary `VariableTerm`;
- the IR does not pretend the complete application is ground when it contains variables.

Consider renaming `FunctionApplication` to `NHerbApplication` and adding an `is_ground`
property only if that improves clarity without creating an unrelated refactor. A narrow union on
its `arguments` field is sufficient for this milestone.

No source-level variable node is needed for ordinary statements that remain pass-through.

## Lowering changes

1. Render `VariableTerm.name` unchanged inside private key terms.
2. Reuse current equality, inequality, and ordered-comparison lowering paths.
3. Keep helper-variable collision detection across every source identifier in the rule.
4. Do not rename source variables.
5. Do not emit domain predicates, value domains, totality rules, or n-variable stand-ins.
6. Keep integer markers limited to the existing supported integer assignment values. Because
   right operands remain ground in this milestone, no dynamic integer-domain mechanism is
   needed.
7. Preserve formatting and source text outside n-atom replacement spans.

The implementation must test that a source variable named `AspfCmp0` or `_AspfCmp0` cannot
collide with generated helpers under modern Clingo’s identifier rules.

## Diagnostics

Every new rejection must raise `UnsupportedSyntaxError` with filename, line, and column.

Recommended messages:

| Condition | Diagnostic text |
| --- | --- |
| no ordinary domain atom | `variable 'A' in a non-Herbrand application must occur in an ordinary positive body atom in the same rule` |
| right-side variable | `variables as n-atom values are not supported in the first variable milestone` |
| underscore-prefixed n-variable | `non-Herbrand variables such as '_V' are not supported by the reference backend` |
| anonymous variable | `anonymous variables are not supported inside n-atoms` |
| nested variable | `variables are supported only as complete direct arguments of a non-Herbrand application` |
| variable key term | `a variable cannot replace the declared non-Herbrand function name` |

Location rules:

- point at the first unsupported variable occurrence in the n-atom;
- if a variable occurs multiple times and has no domain occurrence, report its first n-atom
  occurrence;
- do not point at the operator or whole statement when a precise token span is known;
- comments and string contents never count as variable occurrences or domain providers;
- multi-file diagnostics retain the originating filename.

Do not expose a raw Clingo “unsafe variables” message for a case the frontend can diagnose.

## Conformance fixtures

Add manifest-driven fixtures with explicit semantic-basis labels.

### Accepted fixtures

1. `variable-arg-equality-body`
   - two domain members;
   - one defined matching application;
   - one undefined application;
   - only the defined match derives.
2. `variable-arg-not-equal-body`
   - defined equal, defined different, and undefined keys;
   - only the defined different key derives.
3. `variable-arg-ordered-all-operators`
   - `#<`, `#<=`, `#>`, and `#>=` with negative, zero, and positive values.
4. `variable-arg-ordered-noninteger`
   - symbolic/string left values remain false.
5. `variable-arg-head-assignment`
   - ordinary domain facts ground conditional assignments for each domain member.
6. `variable-arg-functionality-conflict`
   - two domain-grounded distinct head values for one key are unsatisfiable.
7. `variable-arg-repeated-and-multiple-natoms`
   - one domain variable used in multiple supported n-atoms.
8. `variable-arg-multiple-models`
   - ordinary choices determine which grounded assignments exist.
9. `variable-arg-comments-strings-multiline`
   - scanner position and inert-text coverage.
10. `variable-arg-multi-file-domain`
    - declaration, domain, assignment, and comparison distributed across files.

### Rejected fixtures

1. `rejected-variable-arg-unsafe-equality`
2. `rejected-variable-arg-unsafe-not-equal`
3. one unsafe fixture for each of `#<`, `#<=`, `#>`, and `#>=`
4. `rejected-variable-arg-only-negated-domain`
5. `rejected-variable-arg-only-ordinary-comparison-domain`
6. `rejected-variable-arg-only-other-natom-domain`
7. `rejected-variable-value`
8. `rejected-n-variable-value`
9. `rejected-n-variable-argument`
10. `rejected-anonymous-variable-argument`
11. `rejected-nested-variable-argument`
12. `rejected-variable-as-key`
13. existing aggregate, choice, conditional, default-negation, arithmetic, and declared-symbol
    boundary fixtures updated to include variable variants where useful.

Each rejected fixture must assert filename, line, column, and a stable message fragment.

## Test matrix

| Layer | Required tests |
| --- | --- |
| scanner/source | variables across multiline keys; comments and strings inert; exact spans; direct versus nested argument positions |
| frontend | typed variable argument; every operator; head assignment; domain literal before/after n-atom; repeated variable; every rejection and location |
| IR | rendering ground and mixed arguments; equality/hash behavior if used; groundness reporting if added |
| lowering | exact output for head/equality/inequality/order; generated helper freshness; no domain/totality emission; byte preservation outside replacement spans |
| solver | defined true/false, undefined, functionality conflict, noninteger order, negative/zero/positive, multiple models |
| model | stable reconstructed ground assignments; no variables or `__aspf_` atoms leak |
| CLI | human, JSON, and `--emit-lowered`; multiple files; location-aware errors; `--models 0` |
| conformance | all accepted/rejected fixtures and semantic-basis metadata |
| regression | every pre-variable test remains unchanged and passing |

## Acceptance criteria

The implementation is complete only when all of the following hold:

- only files needed for the restricted feature, tests, examples, and documentation change;
- every accepted source variable has an independent ordinary positive body domain occurrence;
- the historically unsafe inequality example is rejected before Clingo grounding;
- undefined applications do not satisfy equality, inequality, or ordered comparisons;
- symbolic/string values never satisfy ordered comparisons;
- no totality or inferred global domain rule is emitted;
- n-variables receive a distinct, explicit unsupported diagnostic;
- ordinary ASP pass-through remains unchanged;
- existing conformance fixtures remain stable;
- formatting, linting, static typing, and all tests pass on Python 3.11 and 3.12.

## Deferred follow-up milestones

The following work must be proposed and reviewed separately:

1. ordinary variables in right/value positions;
2. historical seed-equality-provided safety;
3. application-to-application comparisons;
4. variables nested in ordinary compound key arguments;
5. reified variable keys such as `F #< 0`;
6. Clingo’s broader acyclic-assignment and bounded-comparison safety rules;
7. aggregate, conditional, choice, or disjunctive occurrences;
8. arithmetic expressions;
9. non-Herbrand variables and n-stratification;
10. theory atoms or a native propagator.

None should be folded into the first implementation for convenience.

## Implemented task checklist

The implementation adds **domain-safe ordinary variables in direct declared-key
arguments** with the grammar and safety condition above.

The implementation contract was to:

1. add a typed ordinary-variable argument node with source spans;
2. add a conservative per-rule ordinary-domain safety analysis;
3. render those variables through the existing reference lowering;
4. add the listed frontend, lowering, solver, CLI, and conformance tests;
5. document the new subset and retain explicit n-variable rejection;
6. avoid value variables, historical equality binding, application operands, arithmetic,
   aggregates, and native backend work.

No architectural prerequisite beyond that frontend safety pass and small typed IR extension is
required. The current reference backend is sufficient under these conditions.
