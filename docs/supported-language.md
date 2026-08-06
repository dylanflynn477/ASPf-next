# Supported language: milestone 0.1

This document is normative for the implemented compatibility slice. “Supported”
means parsed into ASP{f} IR and covered by tests. Ordinary Clingo syntax is still
parsed by Clingo after the compatibility frontend has passed it through.

## Declarations

```asp
#nherb balance/1.
#nherb mode/0.
```

Names must be lowercase Clingo identifiers and arities must be non-negative
integers. Declarations may appear after their uses or in another input file
because declaration collection is a separate first pass. Repeating the same
name/arity is accepted. Repeating a name with a different arity is rejected.

Global `#nherb.` and every other declaration spelling are unsupported.

## Applications and arguments

An n-atom key is a declared application with exactly the declared arity:

```asp
balance(account1)
label(product(7), "lot-a")
mode
```

Arguments must be ground. The current term grammar accepts:

- integers, including negative integers;
- lowercase symbolic constants;
- quoted Clingo strings;
- recursively ground ordinary function terms.

Variables, `_v`-style non-Herbrand variables, arithmetic expressions, intervals,
and nested declared non-Herbrand applications are rejected. Zero-arity functions
use the bare form `mode`; `mode()` is also accepted as input and normalized to
`mode`.

## Values

The right side of `#=` is restricted to exactly one:

- integer: `500` or `-3`;
- symbolic constant: `employed`;
- string: `"cold brew"`.

Variables, arithmetic, intervals, tuples, and compound function terms are not
values in this milestone. A declared non-Herbrand application used as a value
receives a specific diagnostic.

## Rule positions

Facts and complete rule heads may assign values:

```asp
balance(account1) #= 500.
status(alice) #= employed :- active(alice).
```

Positive, complete body literals may compare against a value:

```asp
solvent(A) :- account(A), balance(account1) #= 500.
```

The ordinary parts of a rule can still use Clingo variables. Only the n-atom
itself must be ground in this milestone. Several positive n-atoms may appear as
separate comma-delimited body literals.

The following positions are unsupported:

- `not f(a) #= v`;
- n-atoms inside aggregates, choice rules, conditional literals, or disjunctions;
- a head that combines an assignment with another head element;
- nested or parenthesized n-atoms;
- any ambiguous fragment where the n-atom is not a complete supported literal.

## Operators

Only `#=` is recognized semantically. Each of these is explicitly diagnosed at
its source location:

```text
#!=  #<  #<=  #>  #>=
```

## Comments, strings, and statements

The scanner recognizes `%` line comments, `%* ... *%` block comments, escaped
quoted strings, nested parentheses/brackets/braces, multiline statements, and
Clingo interval dots (`..`). ASP{f} markers inside a string or comment are inert.

An ordinary statement with no active ASP{f} syntax is retained as source text.
Its full validity remains Clingo's responsibility. An aggregate with no n-atom,
for example, is ordinary pass-through syntax.

## Visibility and output

Ordinary `#show` directives are preserved and control ordinary shown atoms.
Assignments are reconstructed from all true internal value atoms even if a
`#show` directive is present. All top-level predicates whose names begin with
`__aspf_` are private and omitted from normal human output.

Legacy `#show #nherb` and `#hide #nherb` directives are unsupported.
