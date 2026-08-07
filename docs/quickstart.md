# Quickstart

This tutorial walks through the runnable development surface. It is an
introduction, not the normative language specification; consult
[`supported-language.md`](supported-language.md) for the exact boundary.

## 1. Create an environment

ASPf-next requires Python 3.11 or newer; CI currently tests 3.11 and 3.12. From
the repository root:

```console
python -m venv .venv
```

Activate it on macOS or Linux:

```console
source .venv/bin/activate
```

Or on Windows PowerShell:

```console
.venv\Scripts\Activate.ps1
```

## 2. Install from the checkout

```console
python -m pip install -e ".[dev]"
```

This installs the `aspf` command, Clingo 5.8, and the development tools.

## 3. Run the first program

```console
aspf examples/01_basic_assignment.aspf
```

```text
Answer: 1
solvent(account1) balance(account1)#=500
SATISFIABLE
```

## 4. Declare and assign a partial function

Create `hello.aspf`:

```asp
#nherb balance/1.

balance(account1) #= 500.
```

`#nherb balance/1.` declares a non-Herbrand function named `balance` with one
argument. The `#=` n-atom assigns the integer value `500` to the ground
application `balance(account1)`.

```console
aspf hello.aspf
```

```text
Answer: 1
balance(account1)#=500
SATISFIABLE
```

## 5. Test a value in a rule body

Add a positive body comparison:

```asp
#nherb balance/1.

balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
```

The rule derives `solvent(account1)` because the application has the tested
value. The current frontend requires n-atoms to be ground and does not support
default negation.

## 6. Compare with a different defined value

Positive ground inequality is supported only as a complete body literal:

```asp
#nherb balance/1.

balance(account1) #= 500.
different(account1) :- balance(account1) #!= 600.
```

This derives `different(account1)` because the application is defined as `500`.
If no value had been assigned to `balance(account1)`, the `#!=` literal would
be false. It means “defined and different,” not “no matching equality was
found.”

## 7. Compare defined integers in order

Run the ordered-comparison example:

```console
aspf examples/06_ordered_comparisons.aspf
```

It uses every ordered operator:

```asp
below_zero :- temperature(freezer) #< 0.
at_most_zero :- temperature(freezer) #<= 0.
above_zero :- temperature(room) #> 0.
at_least_twenty :- temperature(room) #>= 20.
```

The application and right operand must be fully ground, and the right operand
must be an integer literal. A comparison succeeds only when the application has
a defined integer value satisfying the usual arithmetic relation. Undefined,
symbolic, and string values make it false; no coercion is performed.

## 8. Inspect the reference lowering

```console
aspf hello.aspf --emit-lowered
```

The significant lowered lines are:

```asp
__aspf_value(balance(account1),500).
__aspf_integer(500).
:- __aspf_value(K,V1), __aspf_value(K,V2), V1 != V2.
```

The first atom represents the value assignment. The constraint enforces at most
one value per ground key. This is an inspectable reference translation, not a
native Clingo propagator.

An inequality such as `balance(account1) #!= 600` lowers to the equivalent of:

```asp
__aspf_value(balance(account1),_AspfNeq0), _AspfNeq0 != 600
```

The required `__aspf_value/2` lookup is what makes an undefined application
fail the comparison.

An ordered comparison additionally requires the private integer marker:

```asp
__aspf_value(balance(account1),_AspfCmp0),
__aspf_integer(_AspfCmp0),
_AspfCmp0 >= 100
```

That marker prevents Clingo's general ordering of symbolic terms from being
mistaken for numeric ASP{f} comparison.

## 9. Use JSON output

```console
aspf examples/03_conditional_assignment.aspf --json
```

```json
{
  "exhausted": false,
  "model_count": 1,
  "models": [
    {
      "assignments": [
        "status(alice)#=employed"
      ],
      "atoms": [
        "active(alice)",
        "status(alice)#=employed"
      ],
      "ordinary_atoms": [
        "active(alice)"
      ]
    }
  ],
  "status": "SATISFIABLE"
}
```

The JSON object separates ordinary shown atoms from reconstructed assignments.
Use `--models 0` when every model is required.

## 10. Understand partiality

Run:

```console
aspf examples/02_partial_function.aspf
```

The program defines `balance(account2)` but not `balance(account1)`. Its model
therefore includes `balance(account2)#=500` and no assignment for `account1`.
Declarations introduce possible function applications; they do not add values
or a totality rule.

## 11. Understand conflicting assignments

```console
aspf examples/04_conflicting_values.aspf
```

```text
UNSATISFIABLE
```

The same ground application is assigned both `500` and `600`, violating the
functionality constraint.

## 12. Recognize unsupported syntax

For example, an ordered comparison cannot use a symbolic right operand:

```asp
#nherb balance/1.
ok :- balance(account1) #>= high.
```

Running it produces a location-aware error resembling:

```text
aspf: error: unsupported.aspf:2:29: operator '#>=' requires an integer literal on the right
```

The same explicit rejection policy covers arithmetic, variables, comparisons in
heads, aggregates containing n-atoms, default-negated n-atoms, and other
deferred constructs. See the [compatibility matrix](compatibility-matrix.md)
before adapting historical ASP{f} programs.
