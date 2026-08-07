# Typed operands and application comparisons plan

## Scope

Implement the next restricted compatibility milestone on
`feature/application-operands`. Body n-atoms may compare two explicitly declared
non-Herbrand applications. Existing scalar assignments and scalar comparisons
remain unchanged. The implementation stays a clean-room Python frontend and
reference translation for unmodified Clingo 5.8.

This branch does not add scalar value variables, historical equality-provided
safety, non-Herbrand variables, arithmetic expressions, aggregates containing
n-atoms, default-negated n-atoms, choices containing n-atoms, theory atoms, or a
native propagator.

## Proposed changes

1. Record the primary-source semantics and the deliberately narrower ASPf-next
   boundary in `docs/design/application-operands.md`.
2. Replace the role-bearing, scalar-specific `NAtom` IR with typed scalar and
   application operands plus distinct `Assignment` and `BodyComparison` nodes.
3. Extend the frontend to parse a declared application as the right operand of
   a complete positive body comparison. Validate declaration, arity, argument
   shape, placement, and source-level safety on both applications.
4. Add a per-statement `TemporaryAllocator` and lower:
   - application equality with a shared generated value variable;
   - application inequality with two defined-value lookups and `!=`;
   - application ordering with two lookups, two integer guards, and the selected
     arithmetic relation.
5. Add focused IR, frontend, lowering, solver, CLI, multi-model, multi-file, and
   manifest-driven conformance coverage. Preserve every existing fixture.
6. Add `examples/08_application_comparisons.aspf` and update user, architecture,
   quickstart, compatibility, roadmap, changelog, and traceability documents.
7. Run formatting, linting, strict type checking, the full suite, the isolated
   conformance suite, a fresh editable install, and manual CLI checks.
8. Review the complete diff against `main`, correct semantic leaks, commit in
   reviewable units, and push the feature branch without merging it.

## Semantic boundary

- A scalar `#=` in a fact or rule head remains an assignment.
- An application-to-application n-atom is a dependent comparison and is accepted
  only as a complete, positive rule-body literal.
- Equality and inequality succeed only when both applications are defined.
  Undefined is neither equal nor unequal.
- Ordered application comparisons succeed only when both applications are
  defined with integer values. Symbols and strings do not participate in Clingo
  term ordering.
- Every source variable in either application key needs its own occurrence in
  an ordinary, unnegated, positive symbolic body atom in the same rule. Private
  lookup atoms and other n-atoms never establish source safety.
- Right-side application operands must be declared and must obey the same
  argument grammar and arity checks as left-side applications.
- Application equality in a head is rejected; it is never lowered as value-copy
  assignment.

## Design concerns

- A bare declared zero-arity symbol on the right is an application operand, not
  a symbolic scalar. An undeclared bare lowercase identifier remains a scalar.
- Generated names must be deterministic and avoid every executable identifier
  in the containing statement, including identifiers that merely resemble the
  allocator's preferred prefix.
- The historical language permits operands and safety modes beyond this
  milestone. The typed IR should expose the present distinction without adding
  a speculative general expression hierarchy.
- The reference lowering is intended for semantic transparency, not the
  grounding-efficiency properties of historical Clingo{f}.
