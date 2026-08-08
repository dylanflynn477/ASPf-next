# Guided examples

Install the project from its repository root before running these examples:

```console
python -m pip install -e ".[dev]"
```

The examples progress from one value assignment to comparisons and ordinary
Clingo model enumeration. They intentionally stay inside the
[documented language boundary](../docs/supported-language.md).

## 01 — Basic assignment and body comparison

[`01_basic_assignment.aspf`](01_basic_assignment.aspf) declares `balance/1`,
assigns one value, and tests that value in a positive rule body.

```asp
#nherb balance/1.

balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
```

```console
aspf examples/01_basic_assignment.aspf
```

The single model contains `solvent(account1)` and
`balance(account1)#=500`. The comparison is positive and ground. Restricted
domain-safe key variables are demonstrated in example 07 and historically
compatible default negation in example 09.

## 02 — Partiality

[`02_partial_function.aspf`](02_partial_function.aspf) declares `balance/1` for
two accounts but assigns a balance only for `account2`.

```asp
#nherb balance/1.

account(account1).
account(account2).
balance(account2) #= 500.
```

```console
aspf examples/02_partial_function.aspf
```

The model contains both accounts and `balance(account2)#=500`, but no balance
assignment for `account1`. A declaration does not make a non-Herbrand function
total; an absent value is undefined.

## 03 — Conditional assignment

[`03_conditional_assignment.aspf`](03_conditional_assignment.aspf) places the
assignment in a rule head.

```asp
#nherb status/1.

active(alice).
status(alice) #= employed :- active(alice).
```

```console
aspf examples/03_conditional_assignment.aspf
```

Because `active(alice)` is true, the model contains
`status(alice)#=employed`. Milestone 0.1 supports only a complete assignment as
the rule head, not disjunctive or choice heads containing n-atoms.

## 04 — Conflicting values

[`04_conflicting_values.aspf`](04_conflicting_values.aspf) assigns two distinct
values to the same ground application.

```asp
#nherb balance/1.

balance(account1) #= 500.
balance(account1) #= 600.
```

```console
aspf examples/04_conflicting_values.aspf
```

The result is `UNSATISFIABLE`. The reference backend adds a functionality
constraint requiring at most one value for each ground key.

## 05 — Ordinary ASP and multiple models

[`05_multiple_models.aspf`](05_multiple_models.aspf) contains no ASP{f} syntax.
It demonstrates ordinary Clingo pass-through and complete model enumeration.

```asp
1 { selected(red); selected(blue) } 1.
#show selected/1.
```

```console
aspf examples/05_multiple_models.aspf --models 0
```

Two models are produced: one selecting `red` and one selecting `blue`. Their
display order is solver-dependent. This is ordinary ASP choice-rule behavior;
choice constructs containing n-atoms remain unsupported.

## 06 — Ordered integer comparisons

[`06_ordered_comparisons.aspf`](06_ordered_comparisons.aspf) exercises all four
positive ground ordered operators with negative, zero, and positive integers.

```asp
#nherb temperature/1.

temperature(freezer) #= -5.
temperature(room) #= 21.

below_zero :- temperature(freezer) #< 0.
at_most_zero :- temperature(freezer) #<= 0.
above_zero :- temperature(room) #> 0.
at_least_twenty :- temperature(room) #>= 20.
```

```console
aspf examples/06_ordered_comparisons.aspf
```

All four ordinary atoms are derived. Ordered comparisons require a defined
integer value and an integer literal on the right. Undefined, symbolic, and
string-valued applications make these comparisons false.

## 07 — Domain-safe variables

[`07_domain_safe_variables.aspf`](07_domain_safe_variables.aspf) uses an
ordinary variable directly as the argument of a declared application.

```console
aspf examples/07_domain_safe_variables.aspf
```

Expected model:

```text
Answer: 1
account(checking) account(savings) low(checking) nonzero(checking) nonzero(savings) balance(checking)#=500 balance(savings)#=1500
SATISFIABLE
```

`A` is accepted because the ordinary positive body atom `account(A)` supplies
its domain. The `savings` balance is defined but not low; an account with no
balance assignment would remain undefined and satisfy neither ordered
comparison nor `#!=`.

## 08 — Application-to-application comparisons

[`08_application_comparisons.aspf`](08_application_comparisons.aspf) compares
observed and expected values without copying either partial function.

```console
aspf examples/08_application_comparisons.aspf
```

Expected model:

```text
Answer: 1
above_expected(b) account(a) account(b) account(c) changed(b) matches(a) actual(a)#=100 actual(b)#=125 expected(a)#=100 expected(b)#=100
SATISFIABLE
```

Both applications are defined and equal for `a`, so `matches(a)` is derived.
They are defined and different for `b`, so `changed(b)` and
`above_expected(b)` are derived. Neither application is defined for `c`, so
none of its comparison rules succeeds. Application equality is a positive body
comparison, not assignment or value-copy syntax.

## 09 - Default negation and undefinedness

[`09_default_negation.aspf`](09_default_negation.aspf) applies default negation
to the positive satisfaction of an ordered n-atom.

```console
aspf examples/09_default_negation.aspf
```

The model includes `needs_review(a)` because `500 >= 1000` is false, excludes
`needs_review(b)` because `1500 >= 1000` is true, and includes
`needs_review(c)` because `balance(c)` is undefined. Undefinedness does not
supply a hidden value: it makes the positive comparison unsatisfied, so its
default negation succeeds.

## Historical compatibility examples

The separate [`historical/`](historical/) directory contains minimal,
attributed programs using historical declaration, scope, arity, and compound
Herbrand-value syntax that now runs unchanged. Deferred historical constructs
remain in the strict compatibility xfail corpus rather than appearing as
runnable examples.

## Portfolio demo

[`portfolio/technical_indicators.aspf`](portfolio/technical_indicators.aspf)
uses a synthetic 14-observation moving average of signed close changes to show
that a defined zero is not missing data. It also uses default negation to request
review when a confidence threshold cannot be established, without calling
default negation an undefinedness test.

```console
aspf examples/portfolio/technical_indicators.aspf --models 0
```

The walkthrough in [`docs/portfolio-demo.md`](../docs/portfolio-demo.md) is
written for readers who know Python but are new to ASP. The example is about
knowledge representation only; it is not a trading system.
