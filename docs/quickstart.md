# Quickstart

This tutorial walks through the runnable milestone 0.1 surface. It is an
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
value. Milestone 0.1 requires n-atoms to be ground and does not support default
negation.

## 6. Inspect the reference lowering

```console
aspf hello.aspf --emit-lowered
```

The significant lowered lines are:

```asp
__aspf_value(balance(account1),500).
:- __aspf_value(K,V1), __aspf_value(K,V2), V1 != V2.
```

The first atom represents the value assignment. The constraint enforces at most
one value per ground key. This is an inspectable reference translation, not a
native Clingo propagator.

## 7. Use JSON output

```console
aspf examples/03_conditional_assignment.aspf --json
```

```json
{
  "exhausted": false,
  "model_count": 1,
  "models": [
    {
      "assignments": ["status(alice)#=employed"],
      "atoms": ["active(alice)", "status(alice)#=employed"],
      "ordinary_atoms": ["active(alice)"]
    }
  ],
  "status": "SATISFIABLE"
}
```

The JSON object separates ordinary shown atoms from reconstructed assignments.
Use `--models 0` when every model is required.

## 8. Understand partiality

Run:

```console
aspf examples/02_partial_function.aspf
```

The program defines `balance(account2)` but not `balance(account1)`. Its model
therefore includes `balance(account2)#=500` and no assignment for `account1`.
Declarations introduce possible function applications; they do not add values
or a totality rule.

## 9. Understand conflicting assignments

```console
aspf examples/04_conflicting_values.aspf
```

```text
UNSATISFIABLE
```

The same ground application is assigned both `500` and `600`, violating the
functionality constraint.

## 10. Recognize unsupported syntax

For example, `#>=` is outside milestone 0.1:

```asp
#nherb balance/1.
ok :- balance(account1) #>= 500.
```

Running it produces a location-aware error resembling:

```text
aspf: error: unsupported.aspf:2:25: operator '#>=' is not supported in the first milestone; only '#=' is
```

The same explicit rejection policy covers arithmetic, variables, aggregates
containing n-atoms, default-negated n-atoms, and other deferred constructs. See
the [compatibility matrix](compatibility-matrix.md) before adapting historical
ASP{f} programs.
