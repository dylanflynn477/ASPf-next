# Supported language

This document is normative for the implemented compatibility slice. “Supported”
means parsed into ASP{f} IR and covered by tests. Ordinary Clingo syntax is still
parsed by Clingo after the compatibility frontend has passed it through.

## Declarations

```asp
#nherb balance/1.
#nherb mode/0.
#nherb status(Account).
#nherb pair(Left,Right).
```

Names must be lowercase Clingo identifiers and arities must be non-negative
integers. Declarations may appear after their uses or in another input file
because declaration collection is a separate first pass. Repeating the same
name/arity is accepted and deduplicated. The same name may be declared at
multiple arities; declaration identity is the exact `(name, arity)` pair.

In the historical application-style form, arguments are placeholders used only
to infer arity. Each placeholder must be an uppercase identifier or `_`; it
does not introduce a program variable and arbitrary expressions are rejected.
The audited sources do not establish an alternative zero-arity spelling, so
zero arity uses `#nherb mode/0.`.

Historical global mode is supported with:

```asp
#nherb.
```

It makes functional expressions under supported `#` connectives
non-Herbrand without per-function declarations. Positive-arity right operands
are applications. A bare right symbol is a zero-arity application only when
its `(name, 0)` signature is established by an explicit declaration or by a
left/key occurrence somewhere in the combined program; otherwise it is a
symbolic scalar value. This whole-program rule is independent of input-file
order. Explicit and global declarations may coexist.

A declaration changes interpretation only under a `#` connective. The same
symbol outside an n-atom retains ordinary Herbrand meaning, so both of these
may coexist without substitution:

```asp
#nherb k/1.
k(1) #= 5.
ordinary(k(1)).
```

## Reserved internal namespace

Every executable user identifier beginning with `__aspf_` is reserved for the
frontend and backends. Such an occurrence raises `UnsupportedSyntaxError` before
lowering. Prefix-like text inside comments and quoted strings is inert.

## Applications and arguments

An n-atom key is an explicitly declared application with exactly the declared
arity, or any valid application under global mode:

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

## Ordinary-variable safety

An ordinary uppercase variable may replace one complete application argument:

```asp
#nherb balance/1.
account(checking;savings).
low(A) :- account(A), balance(A) #< 1000.
balance(A) #= 0 :- account(A), empty(A).
```

An ordinary, unnegated positive symbolic body atom may make its variables safe,
before or after an n-atom. A positive, non-default-negated scalar seed equality
may also provide safety for its direct key variables and optional complete
right value variable:

```asp
p(X) :- balance(X) #= 500.
value_at(X,Y) :- balance(X) #= Y.
```

The reference lowering uses matching `__aspf_value/2` tuples as the finite join
domain. It does not enumerate unrelated constants, add totality, or invent a
value for an undefined key.

Application-to-application equality, inequality, ordered comparison, and every
default-negated n-atom are dependent and do not provide safety. Variables used
there must be made safe by an ordinary positive atom or another positive scalar
seed equality in the same rule. This rule is checked before lowering so a
generated private lookup cannot accidentally make historical P4/P5-style
source programs safe.

Variables inside a compound key argument such as `balance(owner(A))`, anonymous
`_`, and non-Herbrand variables such as `_V` remain unsupported. A declared
application used as the right operand may contain direct variables subject to
the same source-safety rule.

## Values

An assignment value is restricted to exactly one ground term from this list:

- integer: `500` or `-3`;
- symbolic constant: `employed`;
- string: `"cold brew"`;
- undeclared ordinary function term: `k(1)` or `wrapper(k(1))`.

Compound values must be fully ground. Assignment-head value variables,
arithmetic, intervals, and tuples remain unsupported.

In a body n-atom, an ordinary uppercase variable may occupy the entire scalar
right operand. Positive scalar equality can make it safe. Inequality and
default negation may consume it only when another permitted source supplies its
safety. Ordered value variables remain unsupported because an ordinary symbolic
domain does not establish the integer sort required by ASP{f} order.

In a positive body comparison, the right operand may instead be another
explicitly declared non-Herbrand application. This is an application operand,
not an assignment value. The distinction uses exact name/arity: if `k/1` is
undeclared, `k(1)` is a Herbrand scalar value; if `k/1` is declared, the same
text is an application operand whose value must be defined. A declared
application cannot be hidden inside a compound scalar value. A scalar right
operand of `#<`, `#<=`, `#>`, or `#>=` must still be an integer literal; a right
application is validated at runtime as described below.

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

They may also compare two declared applications:

```asp
same(A) :- account(A), actual(A) #= expected(A).
changed(A) :- account(A), actual(A) #!= expected(A).
above(A) :- account(A), actual(A) #> expected(A).
```

A positive `#!=` comparison is true only when the left application has a
defined value and that value differs from the right operand. An undefined
application makes the literal false. Inequality is not negation-as-failure and
is not implemented as the absence of an equality atom.

For application equality and inequality, both application values must be
defined. Equal values satisfy `#=`; different values satisfy `#!=`. An undefined
left operand, undefined right operand, or two undefined operands satisfy
neither relation.

An ordered comparison is true only when the left application has a defined
integer value and the usual arithmetic relation holds against the integer
literal on the right. Undefined, symbolic, and string values make the literal
false. No value is coerced to an integer.

An ordered application-to-application comparison additionally requires the
right application to have a defined integer value. Both values receive integer
guards before the ordinary arithmetic relation is evaluated, so Clingo's
general term ordering cannot make symbolic or string values compare in order.

The ordinary parts of a rule can use normal Clingo variables. A direct
application argument on either comparison side may use the safety rules
described above. A complete scalar value variable is supported for equality and
independently safe inequality. Several positive n-atoms may appear as separate
comma-delimited body literals.

Exactly one `not` may precede any otherwise supported complete body n-atom.
`not L` succeeds when positive `L` is not satisfied. Therefore undefined
equality, inequality, and order all satisfy their default-negated forms. This
is failure of positive satisfaction, not replacement by a complementary
operator. Several positive and default-negated comparisons may coexist in one
rule. Default negation supplies no safety; its variables must be safe elsewhere
in the same rule.

The following positions are unsupported:

- `not not f(a) #= v` and any other prefix beyond one `not`;
- a default-negated assignment or rule head;
- `f(a) op v` in a fact or rule head for every `op` other than `#=`;
- `f(a) #= g(a)` in a fact or rule head; application equality is a dependent
  body comparison and never a copy assignment;
- n-atoms inside aggregates, choice rules, conditional literals, or disjunctions;
- a head that combines an assignment with another head element;
- nested or parenthesized n-atoms;
- any ambiguous fragment where the n-atom is not a complete supported literal.

## Operators

`#=` is supported in the head and body positions described above.
`#!=` is supported only as a complete body literal with a declared
application on the left and a supported ground scalar, independently safe
complete value variable, or declared application on the right. `#<`, `#<=`,
`#>`, and `#>=` are supported only as
complete body literals with an integer literal or declared application
on the right. Application operands on both sides may contain direct domain-safe
ordinary variables. Operator tokens and operand kinds are represented
explicitly in typed IR. `BodyComparison` also records whether the literal is
default-negated; neither polarity nor operators are implemented through
text-wide replacement.

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
`__aspf_` are private and omitted from normal human and JSON model output.
`--emit-lowered` intentionally exposes generated satisfaction helpers because
its purpose is to show the reference translation.

Historical assignment visibility is supported in these forms:

```asp
#hide #nherb.
#hide #nherb f/1.
#show #nherb f/1.
#hide #nherb f(X).
#show #nherb f(X).
```

The default is visible. Directives apply in input order; all-assignment and
exact `(name, arity)` selectors may therefore be combined to hide broadly and
show selectively. They affect reconstructed human/JSON assignments only and
never change solving. `--emit-lowered` omits them.

Modern Clingo 5.8 rejects historical ordinary `#hide.`. ASPf-next accepts that
exact hide-all form, lowers its ordinary-output effect to modern `#show.`, and
also hides all reconstructed assignments. Ordinary modern `#show` directives
continue to pass through independently. Selective ordinary `#hide p/n` is not
translated by this milestone.

## Historical compatibility corpus

The separately attributed historical target lives in
[`tests/historical_compat`](../tests/historical_compat/). It contains 35
matching cases—7 with restrictions and 2 matching rejections of invalid
historical P4/P5 programs—plus 4 intentionally deferred cases and no unresolved
cases.

Explicit declarations, tested partial assignments, scope, and visibility are
historically compatible. Global declarations, the comparison subset,
integer-only order, direct variables, seed safety, and default negation are
historically compatible with restriction. Private predicates and normalized
output are ASPf-next design choices. Choices, aggregates, arithmetic, and
grounder-inert n-variables are not yet compatible; every deferred fixture locks
its expected diagnostic before xfail. See the
[compatibility policy](compatibility/policy.md) and
[historical audit](compatibility/historical-clingof-audit.md). The
[n-variable design](design/non-herbrand-variables.md) records the reference
backend NO-GO.
