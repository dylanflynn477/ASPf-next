# Historical Clingo{f} compatibility audit

Status: living primary-source audit, extended for
`historical-default-negation`.

This is a clean-room language and semantics audit. No historical Clingo{f}
implementation source was consulted. A similar-looking parse is not counted as
compatibility unless the tested behavior also matches the cited semantics.

## Primary sources

| Key | Source | Relevant material |
| --- | --- | --- |
| CF | Marcello Balduccini, [Clingo{f} public documentation](https://mbal.asklab.net/clingof/), last updated 2015-01-16 | Concrete `#` syntax; explicit, alternative, and global declarations; declared/undeclared scope; visibility; P1-P5 safety examples; choices and aggregates. |
| B12 | Marcello Balduccini, ["A 'Conservative' Approach to Extending Answer Set Programming with Non-Herbrand Functions"](https://mbal.asklab.net/papers/bal12.pdf), 2012 | Sections 2-3: seed and dependent t-atoms, partial values, satisfaction, default negation, reduct. |
| B13 | Marcello Balduccini, ["ASP with non-Herbrand Partial Functions: a Language and System for Practical Use"](https://mbal.asklab.net/papers/bal13.pdf), 2013 | Sections 2-3: six n-connectives, arithmetic and aggregate terms, partial semantics, Clingo{f} declarations, name/arity identity, ordinary scope, choices, grounding, n-variables. |
| BG12 | Marcello Balduccini and Michael Gelfond, ["Language ASP{f} with Arithmetic Expressions and Consistency-Restoring Rules"](https://arxiv.org/abs/1301.1387), 2013 | Arithmetic expressions, inequality relations, undefinedness, and CR-rule extension. |

Existing ASPf-next design and traceability documents were also reviewed. They
are implementation records, not independent evidence of historical behavior.

## Semantic baseline

B12 defines a seed equality as an assignment of a constant value to a simple
term. Other comparisons are dependent. A dependent comparison is satisfied
only when both operand values are defined and the relation holds. Default
negation of an n-atom is satisfied when that positive n-atom is not satisfied;
therefore undefinedness makes a positive dependent comparison false and its
default negation true. Functionality excludes two distinct seed values for the
same term, but no totality requirement is imposed.

B13 and CF make operand interpretation scope-sensitive. A declared `f/n`
denotes a non-Herbrand application under a `#` connective. A functional term
whose exact `name/arity` is undeclared is a traditional Herbrand term, and every
occurrence outside an n-atom retains ordinary Herbrand meaning.

## Construct audit

| Construct | Historical syntax | Historical semantics | Primary source | Baseline ASPf-next status | Difficulty | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Explicit declaration | `#nherb f/n.` | Declares the exact non-Herbrand function symbol and arity; arity may be zero. | B13 sec. 3, pp. 551-552; CF Syntax | Compatible | Low | Retain in compatibility-1. |
| Alternative declaration | `#nherb f(X).`, `#nherb pair(X,Y).` | Equivalent explicit declaration; arguments determine arity and do not add rule variables. | CF Syntax | Unsupported | Low | Implement placeholder-only forms in compatibility-1. The sources inspected do not establish an alternative zero-arity spelling. |
| Same name at multiple arities | Separate declarations such as `#nherb f/1.` and `#nherb f/2.` | Declaration identity is `name/arity`; B13 explicitly requires multiple declarations when a name is used at different arities. | B13 sec. 3, p. 552 | Incompatible | Low | Implement `(name, arity)` identity in compatibility-1. |
| Global declaration | `#nherb.` | Function symbols interpreted under `#` connectives are non-Herbrand without individual declarations; ordinary occurrences remain Herbrand. | CF Syntax; B13 sec. 3 | Compatible with restriction | Medium | Implemented as typed program policy. A bare right-side zero-arity application must have an explicit or key-established signature. |
| Equality | `f(a) #= 2`, `f(a) #= g(b)` | Seed equality assigns a constant; dependent equality requires both values defined and equal. | B12 secs. 2-3; B13 secs. 2-3; CF Syntax | Compatible with restriction | Implemented | Retain positive supported positions. Broader values and contexts are separate rows. |
| Inequality | `f(a) #!= 2`, `f(a) #!= g(b)` | Dependent; true only when both values are defined and different. Undefined is not unequal. | B12 secs. 2-3; B13 sec. 2; CF Syntax | Compatible with restriction | Implemented | Retain positive body subset. |
| Ordered relations | `#<`, `#<=`, `#>`, `#>=` | Dependent comparisons under the usual arithmetic interpretation; operands must have defined numerical values. | B13 sec. 2; BG12 sec. 2 | Compatible with restriction | Implemented/high for full language | Retain ASPf-next's documented integer-only subset. Defer arithmetic. |
| Application/application comparison | `f(a) #= k(1)` and analogous dependent operators | If both exact symbols are declared, compare their values; both must be defined. | CF Syntax; B12 secs. 2-3; B13 secs. 2-3 | Compatible with restriction | Implemented | Retain positive body subset. |
| Undeclared functional term under `#` | With only `f/1` declared: `f(a) #= k(1).` | `k(1)` is a Herbrand value identical to itself, not a non-Herbrand invocation. | CF Syntax; B13 sec. 3, p. 552 | Unsupported | Medium | Implement ground compound values, including safe nesting, in compatibility-1. |
| Declared symbol outside n-atoms | `#nherb k/1. ordinary(k(1)).` | The occurrence outside the `#` connective is an ordinary Herbrand term and is not replaced by the value of `k(1)`. | CF Syntax; B13 sec. 3, p. 552 | Incompatible | Low | Remove the global outside-use rejection in compatibility-1; retain private namespace checks. |
| Positive seed equality | `f(a) #= 2.` or as a rule head | A seed literal supports a value assignment; two distinct values are inconsistent; absence remains undefined. | B12 secs. 2-3; B13 sec. 2 | Compatible with restriction | Implemented | Retain reference relation and functionality constraint. |
| Dependent equality | `p :- f(a) #= g(b).` | True only when both defined values are equal; it is not a copy assignment. | B12 secs. 2-3; B13 sec. 2 | Compatible with restriction | Implemented | Retain typed application operands and body-only restriction. |
| Default-negated n-atoms | `not f(a) #= 1`, `not f(a) #!= 1`, `not f(a) #< 1` | `not l` is true exactly when positive `l` is not satisfied. Undefinedness therefore matters and blocks complement rewrites. | B12 sec. 3, pp. 28-30; B13 sec. 2, pp. 550-551; CF examples | Compatible with restriction | Implemented | Retain one complete body `not` over the existing operand/operator/safety subset; never complement the operator. |
| Ordinary-variable safety | CF P1-P3 accepted; P4-P5 rejected | Variables in dependent n-literals follow safety conditions like variables under default negation; positive seed equality can bind terms/values in cases current ASPf-next rejects. | CF Syntax restrictions; B13 sec. 3 | Compatible with restriction | High | Keep independent positive-domain rule in compatibility-1; document P1/P2 xfails and grounding blocker. |
| Non-Herbrand variables | Historical n-variable spelling uses a special prefixed identifier (rendered as `_v` by Clingo{f} documentation/examples). | Treated as grounder-inert value variables; defining n-atoms and n-stratification govern their use and reduce grounding. | B13 sec. 3, pp. 552-553; CF examples | Unsupported | Backend-dependent | Defer. A relational parse alone cannot reproduce grounding behavior. |
| `#hide #nherb` | `#hide #nherb.`, optionally `f/n` or `f(X)` | Hides all or selected seed assignments from displayed models without changing solving. | CF Syntax | Unsupported | Medium | Defer with model-normalization design and strict xfails. |
| `#show #nherb` | `#show #nherb f/1.` or `f(X)` | Selectively shows seed assignments, including in combination with ordinary `#hide.`. | CF Syntax | Unsupported | Medium | Defer with the same output-policy design. |
| N-atoms in choices | `1 { f(X) #= V : d(V) } 1` | Seed n-atoms may occur in choice rules under historical Clingo restrictions. | B13 sec. 3, p. 552; CF ex2 | Unsupported | High | Defer; requires structured choice lowering. |
| N-atoms in aggregates | `count { f(X) #= V : ... }` and n-atoms in aggregate elements | N-atoms participate in aggregate elements; aggregate values include only satisfied elements with defined weights. | B13 sec. 2, pp. 548-550; CF ex2 | Unsupported | High/backend-dependent | Defer. |
| Aggregate terms involving n-atoms | `sum[condition = f(X)]` and related forms | Aggregate terms can be n-atom operands; undefined values are omitted as specified and empty min/max may be undefined. | B13 sec. 2, pp. 548-550 | Unsupported | Backend-dependent | Defer separately from ordinary Clingo aggregates. |
| Arithmetic expressions | `f(y) #= X + 1`, comparisons over arithmetic terms | Arithmetic terms combine numerical constants and non-Herbrand values; undefinedness propagates according to the defined arithmetic rules. | B13 sec. 2; BG12 sec. 2 | Unsupported | High/backend-dependent | Defer; never substitute Clingo term ordering or ordinary syntax accidentally. |

## Findings that control the implemented compatibility subset

1. B13 explicitly resolves the multi-arity question: declarations are keyed by
   `(name, arity)`.
2. CF and B13 explicitly resolve ordinary scope: a declaration changes meaning
   only under `#` connectives.
3. CF explicitly resolves the right functional-term distinction. With `k/1`
   undeclared, `k(1)` is a Herbrand value; with it declared, the same text is an
   application operand whose value must be defined.
4. Ground nested Herbrand terms are representable by modern Clingo. This branch
   accepts them as scalar values only when no exact nested subterm is a declared
   non-Herbrand application; that conservative check prevents a declared
   application from masquerading as data.
5. The inspected source documents `#nherb f(X).` but not a zero-arity
   application-style declaration. ASPf-next therefore keeps `#nherb f/0.` and
   records the alternative spelling as unresolved rather than inventing one.
6. B12 and B13 define `not l` by failure of positive satisfaction and use that
   same test in the reduct. A fresh, parameterized predicate defining positive
   satisfaction reproduces the supported ground instances without treating
   undefinedness as equality or an operator complement.

## Intentionally stricter behavior after this branch

ASPf-next continues to require independent ordinary positive domain atoms for
variables in n-atom keys; accepts ordered comparisons only for integer runtime
values; accepts only one `not` before a complete supported body n-atom; and
rejects n-atoms in choices, aggregates, conditional literals, and arithmetic.
It also reserves executable
identifiers beginning with `__aspf_`. These restrictions are explicit and
tested; none is presented as historical behavior.
