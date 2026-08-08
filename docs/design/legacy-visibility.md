# Legacy non-Herbrand visibility implementation contract

Status: approved for `release/0.2-portfolio-ready`.

## Primary-source contract

The public Clingo{f} documentation defines:

```asp
#hide #nherb.
#hide #nherb f/1.
#show #nherb f/1.
```

Selected forms also have placeholder-style spellings such as
`#show #nherb f(X).`. These directives affect displayed seed assignments, not
their truth or any rule's satisfaction. Historical ordinary `#hide.` hides all
ordinary atoms and seed assignments; the documented selective-show example
uses it before `#show #nherb f/1.`.

## Typed representation

Each accepted non-Herbrand visibility directive becomes an
`NHerbVisibilityDirective` in `Program.nherb_visibility`. A directive contains:

- an explicit `show` or `hide` action;
- either the all-assignments selector or one exact `(name, arity)` selector;
- its source span.

Directives from all input files retain command-line source order. Signature
forms use a non-negative integer arity. Application-style forms accept only
the same uppercase/anonymous placeholders used by historical declarations.
Selectors do not declare functions and do not affect operand classification.

## Output pipeline

```text
solve every assignment normally
        -> reconstruct private value atoms
        -> apply ordered non-Herbrand visibility policy
        -> render human or JSON output
```

The default is visible. Each matching directive updates that assignment's
visibility in source order. Therefore a hide-all followed by show `f/1` exposes
only `f/1`, while a later hide can override an earlier show. Selectors use the
key symbol's exact name and arity, so `f/0`, `f/1`, and `f/2` are independent.

Private predicates beginning with `__aspf_` are always hidden regardless of
the policy. `--emit-lowered` omits legacy non-Herbrand visibility directives
because they have no solver meaning.

## Ordinary Clingo visibility

Modern Clingo 5.8 accepts ordinary `#show` and ASPf-next continues to pass it
through unchanged. It rejects historical `#hide.`. For the exact all-hidden
form only, the compatibility frontend emits modern `#show.`, which establishes
the same empty ordinary shown set and composes with ordinary `#show` selectors.
The same historical directive also adds hide-all to the n-herb policy.

ASPf-next does not introduce a general translation for selective ordinary
`#hide p/n` syntax. Unsupported ordinary syntax remains Clingo's responsibility.

## Semantic invariants

- Visibility never changes lowering rules, functionality, partiality,
  grounding, model count, or stable-model semantics.
- A hidden assignment still satisfies positive and default-negated rules in
  the usual way.
- Human and JSON output apply the same policy and stable ordering.
- Multiple models and multiple files use one deterministic policy.
- Ordinary `#show` and non-Herbrand visibility are independent layers.

## Diagnostics

Only documented all/signature/placeholder forms are accepted. Malformed
selectors, negative arities, extra tokens, invalid placements, or unsupported
application expressions raise a filename-, line-, and column-aware
`UnsupportedSyntaxError`. Directive text in comments and strings is inert.

## Evidence boundary

This milestone implements presentation behavior for reconstructed assignments
and the exact historical ordinary hide-all bridge needed by the documented
selective-show example. It does not add arithmetic, aggregates, choices,
non-Herbrand variables, or new solving semantics.
