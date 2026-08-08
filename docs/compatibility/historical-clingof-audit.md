# Historical Clingo{f} compatibility audit

Status: release-candidate audit through global declarations, visibility,
seed-equality safety, and the n-variable NO-GO decision.

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

The category column uses the project policy literally. “Historically
compatible” always means the attributed executable cases, never the whole
historical language.

| Construct | Audit category | Current tested boundary | Primary basis and remaining restriction |
| --- | --- | --- | --- |
| `#nherb f/n.` | Historically compatible | Exact name/arity declarations, including zero arity and multiple arities | B13 sec. 3; CF Syntax |
| `#nherb f(X).` | Historically compatible | Placeholder-only arguments infer arity | CF Syntax; no alternative zero-arity spelling is claimed |
| Global `#nherb.` | Historically compatible with restriction | Whole-program policy; ordinary occurrences remain Herbrand | CF Syntax; bare right zero-arity applications need an explicit or key-established signature |
| Ground seed assignment and functionality | Historically compatible | Facts and single assignment heads; partiality and conflicting values | B12 secs. 2-3; B13 sec. 2 |
| Scalar equality and inequality | Historically compatible with restriction | Complete body literals over supported scalars; undefined positive comparisons are false | B12 secs. 2-3; broader contexts remain deferred |
| Ordered relations | Historically compatible with restriction | Complete body literals over defined integer values only | B13 sec. 2; BG12 sec. 2; arithmetic terms and ordered value variables are deferred |
| Declared application operands | Historically compatible with restriction | All six body operators compare two defined application values | CF Syntax; body-only and integer-only order restrictions remain |
| Undeclared compound Herbrand value | Historically compatible with restriction | Ground, recursively nested, wholly undeclared function terms | CF Syntax; variables/arithmetic inside values remain unsupported |
| Declared symbol outside an n-atom | Historically compatible | Preserved as an ordinary Herbrand predicate/function occurrence | CF Syntax; B13 sec. 3 |
| Default-negated n-atoms | Historically compatible with restriction | One `not` before a complete supported scalar/application body comparison | B12 sec. 3; B13 sec. 2; no double negation or broader contexts |
| P1/P2 seed-equality safety | Historically compatible with restriction | Positive scalar `#=` supplies rule-local key/value safety through the value relation | CF P1-P2; direct key/complete value variables only |
| P3 dependent safety | Historically compatible with restriction | Ordinary positive atoms or a separate seed equality must supply safety | CF P3; dependent literals remain non-binding |
| P4/P5 unsafe programs | Invalid historical program | Rejected with exact source diagnostics | CF P4-P5; these are passing rejection cases, not unsupported valid features |
| `#hide/#show #nherb` | Historically compatible | Ordered all/exact-name/arity output policy plus historical ordinary hide-all bridge | CF Syntax; selective ordinary legacy hide is not translated |
| Non-Herbrand `_v` variables | Not yet compatible | Location-aware rejection and strict deferred case | B13 sec. 3; reference relational lowering fails grounder-inert behavior; see the [NO-GO design](../design/non-herbrand-variables.md) |
| N-atoms in choices | Not yet compatible | Location-aware rejection and diagnostic-locked deferred case | B13 sec. 3; CF ex2; needs structured choice lowering |
| N-atoms in aggregates | Not yet compatible | Location-aware rejection and diagnostic-locked deferred case | B13 sec. 2; CF ex2; needs structured aggregate IR |
| Arithmetic expressions in n-atoms | Not yet compatible | Location-aware rejection and diagnostic-locked deferred case | B13 sec. 2; BG12 sec. 2; needs separately specified arithmetic/undefinedness |
| `__aspf_` namespace and reference relation | ASPf-next extension/design choice | Reserved executable prefix, `__aspf_value/2`, integer tags, helpers, and stable normalized output | Clean-room backend policy; no historical source claim |

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
   makes no claim for an alternative zero-arity spelling.
6. B12 and B13 define `not l` by failure of positive satisfaction and use that
   same test in the reduct. A fresh, parameterized predicate defining positive
   satisfaction reproduces the supported ground instances without treating
   undefinedness as equality or an operator complement.
7. CF P1-P5 separates positive scalar seed equality from dependent safety. The
   value relation reproduces the supported finite join without an inferred
   global value universe.
8. B13's n-variables are grounder-inert and n-stratified. The measured relation
   rewrite grows by one grounded rule per candidate value, so production
   support is a documented NO-GO for the reference backend.

## Intentionally stricter behavior after this branch

ASPf-next accepts only direct key variables and complete right value variables;
ordered value variables remain unsupported because ordinary domains do not
establish an integer sort. It accepts only one `not` before a complete supported
body n-atom and rejects n-atoms in choices, aggregates, conditional literals,
and arithmetic. It also reserves executable identifiers beginning with
`__aspf_`. These restrictions are explicit and tested; none is presented as
historical behavior.
