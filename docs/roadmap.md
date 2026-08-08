# Roadmap

This roadmap distinguishes shipped behavior from possible research directions.
Items beyond the implemented surface are proposals, not commitments or
compatibility claims.

## Milestone 0.1 — restricted reference frontend

Implemented:

- location-aware compatibility scanning and validation;
- `#nherb f/n.` declarations;
- ground `#=` assignments in facts and complete rule heads;
- positive ground `#=` comparisons in rule bodies;
- integer, symbolic constant, and string values;
- inspectable reference lowering to ordinary Clingo 5.8;
- partiality and functionality without a totality rule;
- model enumeration, normalized human output, and JSON output; and
- explicit diagnostics for unsupported ASP{f}-shaped syntax.

See the [supported-language document](supported-language.md) for the normative
boundary.

## Milestone 0.2 conformance foundation

Implemented without changing the milestone 0.1 accepted language:

- map every milestone 0.1 construct to primary sources, implementation, tests,
  and known deviations;
- execute a machine-readable conformance corpus across source layout and
  multi-file programs; and
- record the architectural decisions that protect the semantic boundary.

## Implemented compatibility increments

Positive ground `#!=` is implemented as a complete positive body literal. Both
operands must be defined, so an undefined left application makes the comparison
false. The reference backend performs an explicit value lookup followed by
ordinary inequality; it does not treat inequality as the absence of equality.
No release number has been assigned to this increment.

Positive `#<`, `#<=`, `#>`, and `#>=` body literals are also implemented for
integer values and integer scalar right operands.
Undefined and non-integer application values make the comparison false. No
coercion or arithmetic is included, and no release number has been assigned.

The initial domain-safe ordinary-variable increment implemented complete direct application
arguments with independent ordinary positive domains. The later seed-equality
increment adds rule-local safety for positive scalar equality and complete body
value variables. Nested argument variables, ordered value variables, anonymous
variables, and `_v` non-Herbrand variables remain unsupported. These increments
have no release number yet.

Typed scalar and application operands are implemented in distinct assignment
and body-comparison IR nodes. Positive application-to-application equality and
inequality require both values to be defined; all four ordered operators also
require both runtime values to be integers. Application comparison remains
body-only and does not provide source-variable safety or assignment/copy
semantics.

## Historical compatibility 1

Implemented as an unreleased compatibility subset:

- application-style explicit declarations such as `#nherb f(X).`;
- exact `(name, arity)` identity, including same-name declarations at multiple
  arities;
- ordinary Herbrand use of declared symbols outside n-atoms;
- ground compound Herbrand values under equality and inequality; and
- typed declared-versus-undeclared functional operands.

The milestone established the attributed historical corpus and its
manifest-derived report. After the seed-equality increment, the corpus has 39
cases: 35 pass and 4 are expected unsupported, with no unresolved cases.
Choices, aggregates, arithmetic, and n-variables remain visible strict xfails. See the
[audit](compatibility/historical-clingof-audit.md) and
[policy](compatibility/policy.md). No release number has been assigned.

## Historical default negation

One `not` before an otherwise supported complete body n-atom is implemented
for scalar and application operands, all six operators, and source-safe key and
value variables. It means failure of positive
satisfaction: an undefined operand makes default-negated equality, inequality,
and ordering true. The reference backend defines positive satisfaction with a
fresh parameterized helper and negates that helper, preserving the supported
reduct behavior without complementing operators.

## Historical global declaration mode

Global `#nherb.` is implemented as typed program policy across all input files.
It affects functional expressions only under supported `#` connectives and
keeps ordinary occurrences Herbrand. Positive-arity right expressions are
applications; an ambiguous bare right token is a zero-arity application only
when an explicit declaration or key occurrence establishes that signature.
The historical case now passes with this documented restriction.

## Historical non-Herbrand visibility

Hide-all, exact selective hide, and exact selective show are implemented as
typed presentation policy applied after solving. Placeholder selector forms,
multiple arities, files, models, and human/JSON parity are covered. Historical
ordinary `#hide.` is bridged to modern `#show.` so the documented selective-show
example passes without changing stable-model semantics.

## Historical seed-equality safety

Positive, non-default-negated scalar `#=` now supplies rule-local safety for
direct key variables and an optional complete right value variable. The
reference backend uses the positive value relation as the finite join domain;
it adds no totality or inferred value-universe rules. Dependent comparisons and
default negation remain non-binding, while ordered value variables remain
deferred for lack of a source integer sort.

## Next compatibility candidates

Arithmetic expressions, broader variable positions, and every broader n-atom
context remain deferred. Each candidate requires its own primary-source review,
explicit undefinedness rule, typed IR, conservative diagnostics, and focused
conformance cases.

## Non-Herbrand variable decision

Historical `_v` n-variables are a reference-backend NO-GO. They are
grounder-inert, equality-defined, n-stratified solver values; replacing them by
ordinary Clingo variables reproduces simple copy models but adds one grounded
rule per candidate value. Replacing them by constants is semantically wrong.
The strict deferred case therefore remains, backed by the
[design analysis](design/non-herbrand-variables.md) and a reproducible probe
under `research/`. A future theory-atom/custom-propagator backend is the next
credible implementation route, not part of this release.

## Later research

Longer-term topics may include:

- additional comparisons and arithmetic;
- a theory/propagator backend for non-Herbrand variables and broader semantics;
- aggregates containing n-atoms;
- an alternative backend using Clingo theory atoms or a custom propagator;
- equivalence and grounding-size studies comparing backends; and
- an explainable portfolio-risk demonstration built only after the language
  semantics it needs are specified and tested.

None of these later language capabilities is implemented by the current
increments. A native backend would be a separate research
milestone, not a silent replacement for the reference translation.
