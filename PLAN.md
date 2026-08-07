# Historical compatibility 1 plan

## Scope

Work on `feature/historical-compatibility-1`, starting from the merged typed
operand/application-comparison milestone. Establish an attributed, executable
historical Clingo{f} compatibility target and implement only the low- and
medium-risk compatibility slices whose semantics are directly supported by
primary sources.

This branch remains a clean-room Python frontend and reference translation for
the official Clingo 5.8 package. It will be pushed for review but not merged or
released as part of this work.

## Source-backed implementation slices

1. Accept historical application-style explicit declarations such as
   `#nherb f(X).`, using placeholders only to infer arity.
2. Identify declarations by `(name, arity)` so the same name can be declared at
   multiple arities, as explicitly documented for Clingo{f}.
3. Restore ordinary Herbrand meaning for declared symbols outside `#`
   connectives. A declaration affects operand interpretation only within an
   n-atom.
4. Accept undeclared, ground compound Herbrand values under equality and
   inequality, including nested terms. A declared application in the same
   operand position remains an application operand and must be defined.
5. Preserve the existing integer-only ordered-comparison policy, source-safety
   policy, private namespace reservation, partiality, functionality, model
   normalization, multi-file behavior, and deterministic lowering.

## Compatibility infrastructure

1. Record the primary-source audit in
   `docs/compatibility/historical-clingof-audit.md` and define compatibility
   terminology in `docs/compatibility/policy.md` before production changes.
2. Add an attributed manifest and parameterized suite under
   `tests/historical_compat/`. Passing cases are regression contracts;
   historically valid deferred cases are strict `xfail` tests.
3. Add `scripts/compatibility_report.py`, generated entirely from manifest
   metadata, and run the historical suite separately in CI.
4. Recreate a small set of minimal, attributed, runnable programs under
   `examples/historical/` without consulting or copying historical
   implementation source.
5. Update the README, changelog, roadmap, compatibility matrix, traceability,
   supported-language, architecture, and contributing documentation without a
   blanket backward-compatibility claim.

## Researched deferments

The following receive attributed fixtures and design notes but no production
implementation in this branch unless the audit proves a small, exact reference
translation:

- global `#nherb.`;
- legacy `#show #nherb` and `#hide #nherb` visibility controls;
- historical equality-provided ordinary-variable safety;
- default-negated n-atoms.

Non-Herbrand variables, arithmetic expressions, n-atoms in choices or
aggregates, aggregate terms involving n-atoms, native theory atoms, a custom
propagator, CR-rules, and optimization semantics are explicitly out of scope.

## Verification and delivery

Run formatting, linting, strict type checking, the full suite, the existing
conformance suite, and the historical compatibility suite. Then perform a
clean editable install and manually exercise every supported historical
example, lowered output, and JSON output. Review the complete diff against
`main`, commit in reviewable units, and push
`feature/historical-compatibility-1` without merging it or publishing a
release.

## Design concerns

- Application-style declaration arguments are declaration placeholders, not
  executable expressions or program variables. The audit does not establish a
  historical alternative zero-arity spelling, so `#nherb f/0.` remains the
  supported zero-arity form.
- Right-side functional syntax is scope-sensitive: an exact declared
  `(name, arity)` denotes an application operand; otherwise it is a ground
  Herbrand value. Nested declared applications must not silently masquerade as
  scalar values.
- Historical global mode makes zero-arity terms and ordinary predicate syntax
  context-sensitive. It will not be approximated by guessed declarations.
- Historical visibility is output policy, not solver semantics, and needs an
  explicit model-normalization representation before implementation.
- Historical seed-equality safety and non-Herbrand variables were designed in
  part to change grounding behavior. The current relational backend must not
  claim those semantics by merely weakening source validation.
