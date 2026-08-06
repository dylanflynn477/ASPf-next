# Guided examples

Install the project from its repository root before running these examples:

```console
python -m pip install -e ".[dev]"
```

The examples progress from one value assignment to ordinary Clingo model
enumeration. They intentionally stay inside the
[milestone 0.1 language boundary](../docs/supported-language.md).

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
`balance(account1)#=500`. The comparison is positive and ground; variables and
default-negated n-atoms are not supported.

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
