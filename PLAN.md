# Historical default-negation plan

## Scope

Work on `feature/historical-default-negation`, starting from the merged
historical-compatibility-1 milestone. Implement default-negated n-atoms only
for the scalar, application/application, operator, and independently
domain-safe ordinary-variable forms that positive body comparisons already
support.

This remains a clean-room Python frontend and correctness-oriented reference
translation for the official Clingo 5.8 package. The branch will be pushed for
review but not merged or released as part of this work.

## Ordered work

1. Reconfirm satisfaction and reduct semantics from the historical Clingo{f}
   documentation, Balduccini 2012, and Balduccini 2013. Replace the existing
   deferment note with an implementation contract and complete undefinedness
   truth tables before production changes.
2. Add explicit negation polarity to the typed `BodyComparison` IR. Parse one
   `not` before a complete supported body n-atom and keep assignments and rule
   heads non-negated.
3. Lower each default-negated comparison through a fresh private predicate
   that defines positive satisfaction, then default-negate that predicate in
   the source rule. Parameterize helpers by every source variable occurring in
   either operand, in stable first-occurrence order. Allocate helper identities
   from lowering-local state, never module-global mutable state.
4. Add focused frontend, lowering, solver, model, and CLI tests for defined and
   undefined equality, inequality, all ordered operators, application operands,
   variables, multiple comparisons, multiple models, and recursive/reduct
   cases. Retain location-aware rejection of double negation, unsafe variables,
   invalid heads, aggregates, choices, conditional literals, arithmetic, and
   non-Herbrand variables.
5. Convert the historical default-negation xfails only after their semantics
   pass. Add attributed historical fixtures and separate ASPf-next conformance
   cases, then regenerate the compatibility report solely from manifest data.
6. Update the public documentation and add
   `examples/09_default_negation.aspf`, emphasizing that undefinedness makes
   the positive comparison unsatisfied rather than supplying a hidden value.
7. Run formatting, linting, strict typing, all suites, the compatibility
   report, a clean editable install, and the required manual CLI scenarios.
   Review the complete diff against `main`, commit in reviewable units, and
   push the feature branch without merging it.

## Semantic and architectural constraints

- `not L` is failure of positive satisfaction, never an operator complement.
- A helper body contains only the literals needed to establish the positive
  n-atom. Ordinary source-domain literals stay in the source rule; frontend
  safety is checked before lowering and cannot be supplied by generated code.
- Fresh helper predicates use the reserved `__aspf_` namespace, have one
  deterministic identity per negated comparison, and are filtered from normal
  and JSON model output. `--emit-lowered` intentionally exposes them.
- The helper is a one-way exact definition of positive satisfaction. Replacing
  `not L` with default negation of this fresh atom preserves the supported
  fragment's reduct test while allowing the original assignment dependency
  cycles to remain visible to Clingo.
- Positive comparison lowering must remain byte-for-byte stable apart from
  unavoidable shared refactoring covered by regression tests.

## Explicit non-goals

Do not implement global `#nherb.`, legacy visibility directives, historical
seed-equality safety expansion, right-side value variables, non-Herbrand
variables, arithmetic, aggregates, n-atoms in choices or conditional literals,
or a native theory/propagator backend.
