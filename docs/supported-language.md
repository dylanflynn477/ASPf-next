# Supported language

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

Once declared, a non-Herbrand symbol may occur only as the key of a supported
n-atom. Using it as an ordinary predicate or Herbrand function term is rejected,
including `balance(account1).` and `p(balance(account1)).`.

## Reserved internal namespace

Every executable user identifier beginning with `__aspf_` is reserved for the
frontend and backends. Such an occurrence raises `UnsupportedSyntaxError` before
lowering. Prefix-like text inside comments and quoted strings is inert.

## Applications and arguments

An n-atom key is a declared application with exactly the declared arity:

```asp
balance(account1)
label(product(7), "lot-a")
mode
```

The current argument grammar accepts:

- integers, including negative integers;
- lowercase symbolic constants;
- quoted Clingo strings;
- recursively ground ordinary function terms.
- an ordinary uppercase variable as one complete, direct argument, provided it
  satisfies the source-level safety rule below.

Variables nested inside compound arguments, `_v`-style non-Herbrand variables,
anonymous variables, arithmetic expressions, intervals, and nested declared
non-Herbrand applications are rejected. Zero-arity functions use the bare form
`mode`; `mode()` is also accepted as input and normalized to `mode`.

## Domain-safe ordinary variables

An ordinary uppercase variable may replace one complete application argument:

```asp
#nherb balance/1.
account(checking;savings).
low(A) :- account(A), balance(A) #< 1000.
balance(A) #= 0 :- account(A), empty(A).
```

Every variable used in any n-atom key in a rule must also occur in an ordinary,
unnegated positive symbolic body atom in that same rule. The domain atom may
appear before or after the n-atom. A generated `__aspf_value` lookup, another
n-atom, ordinary equality or comparison, a default-negated atom, and a
classically negated atom do not establish source-variable safety.

This deliberately narrower rule is checked before lowering. It prevents a
private backend variable or lookup from accidentally widening the source
grounding domain. Variables on the right, variables inside a compound key
argument such as `balance(owner(A))`, anonymous `_`, and non-Herbrand variables
such as `_V` remain unsupported.

## Values

The right side of `#=` or a supported `#!=` body comparison is restricted to
exactly one:

- integer: `500` or `-3`;
- symbolic constant: `employed`;
- string: `"cold brew"`.

Variables of every kind, arithmetic, intervals, tuples, and compound function
terms are not values in this milestone. A declared non-Herbrand application
used as a value receives a specific diagnostic.

The right operand of `#<`, `#<=`, `#>`, and `#>=` is narrower: it must be an
integer literal. Symbolic constants and strings are rejected in that position.

## Rule positions

Facts and complete rule heads may assign values:

```asp
balance(account1) #= 500.
status(alice) #= employed :- active(alice).
```

Positive, complete body literals may compare against a value:

```asp
solvent(A) :- account(A), balance(account1) #= 500.
different :- balance(account1) #!= 600.
negative :- balance(account1) #< 0.
within_limit :- balance(account1) #<= 500.
positive :- balance(account1) #> 0.
minimum_met :- balance(account1) #>= 100.
```

A positive `#!=` comparison is true only when the left application has a
defined value and that value differs from the right operand. An undefined
application makes the literal false. Inequality is not negation-as-failure and
is not implemented as the absence of an equality atom.

An ordered comparison is true only when the left application has a defined
integer value and the usual arithmetic relation holds against the integer
literal on the right. Undefined, symbolic, and string values make the literal
false. No value is coerced to an integer.

The ordinary parts of a rule can use normal Clingo variables. A direct n-atom
key argument may use the domain-safe subset described above; its right operand
must remain ground. Several positive n-atoms may appear as separate
comma-delimited body literals.

The following positions are unsupported:

- `not f(a) #= v`;
- `not f(a) #!= v`;
- default-negated ordered comparisons;
- `f(a) op v` in a fact or rule head for every `op` other than `#=`;
- n-atoms inside aggregates, choice rules, conditional literals, or disjunctions;
- a head that combines an assignment with another head element;
- nested or parenthesized n-atoms;
- any ambiguous fragment where the n-atom is not a complete supported literal.

## Operators

`#=` is supported in the head and positive-body positions described above.
`#!=` is supported only as a complete, positive body literal with a declared
application on the left and a supported ground value on the right. `#<`, `#<=`,
`#>`, and `#>=` are supported only as complete, positive body literals with an
integer literal on the right. The left key may contain direct domain-safe
ordinary variables. Operator tokens are represented explicitly in typed IR;
they are not implemented through text-wide replacement.

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
