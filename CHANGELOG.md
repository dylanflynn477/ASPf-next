# Changelog

Notable changes to ASPf-next are recorded here. The project uses
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) structure and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) for reader-facing
releases. Python package metadata uses the equivalent PEP 440 version.

## Unreleased

### Added

- Primary-source traceability for every milestone 0.1 construct and known
  compatibility deviation.
- A manifest-driven conformance corpus covering accepted and rejected syntax,
  solving behavior, partiality, functionality, model enumeration, source
  layout, and multiple files.
- Architecture decision records for clean-room development, reference
  lowering, partiality, conservative rejection, and the private backend
  namespace.
- Positive, ground `#!=` comparisons as complete rule-body literals. The left
  application must be defined, and its value must differ from the restricted
  ground right operand.
- Typed comparison operators in the ASP{f} IR and definedness-aware reference
  lowering through an explicit value lookup.
- Focused frontend, lowering, solver, CLI, and conformance regressions for
  inequality behavior and its unsupported contexts.
- Positive, fully ground `#<`, `#<=`, `#>`, and `#>=` comparisons as complete
  rule-body literals with integer literals on the right.
- Definedness- and type-aware reference lowering that tags integer assignment
  values before applying a shared ordinary comparison path.
- Ordered-comparison conformance fixtures, CLI regressions, and a sixth guided
  example covering negative, zero, and positive values.
- Typed ordinary variables in direct non-Herbrand application arguments, with
  source spans and a conservative source-level domain-safety check.
- Domain-safe variable lowering for assignment heads and all six supported
  scalar body operators while keeping each scalar right operand ground.
- Focused frontend, lowering, solver, CLI, and conformance regressions plus a
  seventh guided example for restricted ordinary variables.
- Typed scalar and application operands with distinct assignment and positive
  body-comparison IR nodes.
- Definedness-aware application-to-application `#=` and `#!=`, plus integer-only
  application-to-application `#<`, `#<=`, `#>`, and `#>=` comparisons.
- A deterministic statement-local temporary allocator, expanded conformance
  coverage, multi-file and multi-model regressions, and an eighth guided
  example for comparing expected and observed values.
- Historical application-style declarations such as `#nherb f(X).`, with
  placeholder-only arity inference and harmless equivalent duplicates.
- Exact `(name, arity)` declaration identity, including same-name declarations
  at multiple arities and zero-arity coexistence.
- Historical scope behavior: declared symbols retain ordinary Herbrand meaning
  outside `#` connectives.
- Ground compound Herbrand assignment and comparison values, with typed
  declared-versus-undeclared right operand disambiguation.
- An attributed 39-case historical compatibility corpus: 31 passing cases, 6
  expected unsupported cases, and 2 unresolved safety cases, plus a
  manifest-derived report and independent CI invocation.
- Primary-source audit, compatibility policy, deferment designs, and runnable
  historically styled examples.
- Historically compatible default-negated n-atoms for all six currently
  supported body operators, scalar and application operands, and independently
  domain-safe key variables.
- Explicit comparison polarity in the typed IR and deterministic private
  positive-satisfaction helpers that preserve undefinedness without operator
  complementation.
- Historical and conformance matrices for defined, false, undefined,
  application, variable, recursive, and multi-model default-negation behavior,
  plus a ninth guided example.
- Historical global `#nherb.` mode as typed program policy, including
  multi-file signature collection, zero-arity key resolution, ordinary
  Herbrand coexistence, and an explicit bare-right signature restriction.

No release number has been assigned to these development increments.

## 0.1.0-alpha - Unreleased

### Added

- Location-aware scanning for comments, strings, multiline statements, and
  nested delimiters.
- A restricted compatibility frontend for `#nherb f/n.`, ground `#=` head
  assignments, and positive ground body comparisons.
- Typed ASP{f} intermediate representations and an inspectable reference
  translation to `__aspf_value/2` with a functionality constraint.
- Clingo 5.8 solving, model enumeration, stable ASP{f}-style reconstruction,
  JSON output, and lowered-source output.
- Explicit diagnostics for deferred syntax and reserved internal identifiers.
- Guided examples, tutorial, reproducible terminal demos, architecture and
  provenance documentation, and Python 3.11/3.12 CI.

### Known limitations

The current unreleased package does not implement right-side scalar variables,
historical equality-provided safety,
non-Herbrand variables, arithmetic inside n-atoms, n-atoms in aggregates or
choices, or a native theory-atom/propagator backend. It does not claim full
historical ASP{f} compatibility.
