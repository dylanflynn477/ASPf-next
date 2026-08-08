# Global `#nherb.` implementation contract

Status: approved for `release/0.2-portfolio-ready`.

## Primary-source contract

The public Clingo{f} documentation states that `#nherb.` makes all function
symbols under `#` connectives non-Herbrand without individual declarations.
It separately states that occurrences outside n-atoms retain their ordinary
Herbrand interpretation. Balduccini 2013 describes the same scope boundary:
terms outside an n-atom remain Herbrand, which preserves reification.

The implementation therefore treats global mode as an operand-interpretation
policy, not as a source rewrite and not as a declaration guessed for every
identifier in the program.

## Typed representation

`Program.global_nherb` records whether any input source contains a valid
top-level `#nherb.` declaration. Explicit declarations remain represented by
`NHerbDeclaration` and may coexist with global mode. Declaration collection is
performed across all input sources before any executable statement is parsed,
so file order does not change operand classification.

The frontend also builds a whole-program set of application keys established
by the left side of n-atoms. This set is parser metadata, not synthesized
declaration text. It is needed only to distinguish zero-arity applications from
symbolic constants on the right.

## Operand classification

With global mode active:

- every syntactically valid left application under a supported `#` connective
  is a non-Herbrand application;
- every positive-arity functional expression used as a complete right operand
  under `#` is a non-Herbrand application;
- a bare right symbol is a zero-arity application only if `(name, 0)` is
  established by an explicit declaration or by use as an n-atom key somewhere
  in the combined program;
- every other bare right symbol is a scalar Herbrand constant;
- integer and string right operands remain scalar values;
- nested applications, arithmetic, variables in values, aggregates, choices,
  and other currently unsupported forms remain rejected;
- every occurrence outside an n-atom is passed through unchanged, including
  ordinary atoms and function terms with the same spelling and arity.

This classification is independent of source-file order. For example, a
right-side `mode` may be recognized as the zero-arity application `mode` even
when `mode #= active.` occurs in a later file.

## Zero-arity restriction

Clingo surface syntax does not lexically distinguish a symbolic constant from
a zero-arity function. The public documentation establishes both symbolic seed
values and zero-arity applications, but does not specify a separate spelling
for a bare right-side zero-arity application under global mode.

ASPf-next therefore requires a zero-arity function signature to be established
by an explicit declaration or by a left/key occurrence. A bare symbol that
appears only on the right remains a scalar constant. This is a documented
compatibility restriction; the frontend does not infer an otherwise invisible
zero-arity function from intent.

## Multi-file and mixed declarations

A valid global declaration in any input file activates global mode for the
combined program. Explicit declarations from any file continue to contribute
exact `(name, arity)` identities, including zero arity. Repeated global or
explicit declarations are idempotent. Comments and strings containing
`#nherb.` are inert.

## Semantic invariants

- Global mode introduces no totality rule. An application without a value
  lookup remains undefined.
- Functionality remains enforced by the existing private value relation.
- Global mode does not change ordinary Clingo predicates, terms, `#show`
  behavior, or model solving outside n-atoms.
- It does not weaken source-variable safety.
- It does not permit private `__aspf_` identifiers.
- It does not change the integer-only restriction of the reference ordered
  comparison backend.

## Diagnostics

Only a complete top-level `#nherb.` statement activates global mode. Arguments,
suffixes, rule placement, or malformed spellings receive a location-aware
`UnsupportedSyntaxError`. Legacy `#show/#hide #nherb` directives remain a
separate milestone and are not parsed as global declarations.

## Evidence boundary

This milestone demonstrates the documented global declaration behavior for the
currently supported ASPf-next n-atom fragment. It does not claim support for
historical arithmetic, aggregates, choices, non-Herbrand variables, or native
Clingo{f} grounding behavior.
