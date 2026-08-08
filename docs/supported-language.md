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
grounding domain. Scalar variables on the right, variables inside a compound
key argument such as `balance(owner(A))`, anonymous `_`, and non-Herbrand
variables such as `_V` remain unsupported. A declared application used as the
right operand may contain direct variables, but each one needs the same
independent ordinary domain occurrence.

## Values

An assignment value or scalar comparison operand is restricted to exactly one
ground term from this list:

- integer: `500` or `-3`;
- symbolic constant: `employed`;
- string: `"cold brew"`;
- undeclared ordinary function term: `k(1)` or `wrapper(k(1))`.

Variables of every kind, arithmetic, intervals, and tuples are not scalar
values in this milestone. Compound values must be fully ground.

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
application argument on either comparison side may use the domain-safe subset
described above. Scalar right operands remain ground. Several positive n-atoms
may appear as separate comma-delimited body literals.

Exactly one `not` may precede any otherwise supported complete body n-atom.
`not L` succeeds when positive `L` is not satisfied. Therefore undefined
equality, inequality, and order all satisfy their default-negated forms. This
is failure of positive satisfaction, not replacement by a complementary
operator. Several positive and default-negated comparisons may coexist in one
rule. Every variable keeps the same independent ordinary positive-domain
requirement.

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
application on the left and either a supported ground scalar or declared
application on the right. `#<`, `#<=`, `#>`, and `#>=` are supported only as
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
[`tests/historical_compat`](../tests/historical_compat/). Passing cases lock the
supported historical subset; strict xfails expose equality-provided safety,
choices, aggregates, arithmetic, and non-Herbrand variables. See the
[compatibility policy](compatibility/policy.md) and
[historical audit](compatibility/historical-clingof-audit.md).
