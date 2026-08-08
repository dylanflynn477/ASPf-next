# Historical non-Herbrand variables

Status: **NO-GO for the current reference backend**. Historical n-variable
syntax remains rejected and its compatibility case remains a strict xfail.

This is a clean-room design analysis based on the public Clingo{f}
documentation and Balduccini's 2013 ASP{f} paper. No historical implementation
source code was consulted.

## Primary-source properties

### Spelling and lexical identity

Historical Clingo{f} calls these expressions non-Herbrand variables or
n-variables. The paper describes an alphanumeric name prefixed by `_`, with
examples rendered as `_v` and `_x12`. The project request commonly uses `_V`.
ASPf-next currently recognizes underscore-prefixed variable-shaped tokens only
to reject them precisely; it does not claim that every case variant was
accepted by every historical release.

An n-variable must be a distinct future IR node. It is not an ordinary source
variable, Clingo variable, anonymous `_`, or symbolic constant.

### Grounder behavior and motivation

B13 section 3 states that n-variables are considered ground expressions and
are not affected by grounding. They were introduced because an ordinary value
variable makes a rule's grounding grow with the value domain even though a
non-Herbrand application can have only one value in a model.

The motivating transformation replaces an ordinary variable in a rule like
the following conceptual pattern:

```asp
f(y) #= X + 1 :- d(X), f(x) #= X.
```

with a grounder-inert n-variable:

```asp
f(y) #= _x + 1 :- f(x) #= _x.
```

The second rule remains ground, so its grounding size does not vary with
`d/1`. Preserving only the final model while reintroducing that enumeration is
not historical n-variable compatibility.

### Defining equalities and n-stratification

For a ground rule, a defining n-atom for n-variable `ν` has form `ν #= t` or
`t #= ν`. An index assignment gives every n-variable a positive integer and
gives constants and simple terms index zero. The index of a compound term is
the maximum index of its components.

A rule is n-stratified only when every n-variable has a positive defining
equality whose other term has a strictly smaller index. Every rule containing
n-variables must be n-stratified. This excludes definition cycles such as
`_x #= _y, _y #= _x` and self-definition `_x #= _x` because no strict index
ordering exists.

N-variables cannot occur as arguments of simple terms or aggregate terms.
Consequently `balance(_v)` is invalid even though `_v` can occur as an operand
or inside a permitted arithmetic term.

### Interaction with ordinary variables

Ordinary variables are replaced during grounding. N-variables are retained as
ground expressions. A source rule may therefore be instantiated over its
ordinary variables while each resulting ground rule keeps its own n-variable
value state. Flattening both categories into `VariableTerm` would merge these
two stages and erase the reason n-variables exist.

### Values, undefinedness, and multiple definitions

The historical propagation account maintains values for simple terms and
n-variables. A value is a constant or an explicit undefined state.

Within one rule, an n-variable receives value `v` when every positive defining
equality has a right-hand term with value `v`. Multiple definitions agreeing on
one value therefore agree on the n-variable. If two defining right-hand terms
have different values, the n-variable becomes undefined. A single undefined
definition likewise supplies the undefined state rather than an ordinary
symbol named `undefined`.

This behavior is not ordinary unification. It also is not the functionality
constraint for a non-Herbrand application: n-variable definition consistency
is rule-local solver state used to evaluate that rule's n-atoms.

### Comparisons, default negation, and arithmetic

A body n-atom is true when both operand values are defined and satisfy its
relation. It is false when a value is undefined or the defined values fail the
relation. Default negation is then evaluated from that positive satisfaction
result.

N-variables may stand where traditional value variables stand subject to their
definition and placement restrictions. Arithmetic terms may contain them; the
term's value is computed after the defining values are available, and
undefinedness propagates. This is a solver-time operation, not ordinary Clingo
ground arithmetic.

### Program cycles beyond n-stratification

B13 separately defines an n-loop as a positive dependency path connecting
n-atoms that share a simple term. The paper states soundness and completeness
of the described historical engine for n-loop-free programs. A future
compatibility target must preserve this distinction instead of treating
rule-local n-stratification as the only cycle condition.

## Reference-translation candidates

### Ordinary relational join

For a simple copy rule:

```asp
h(x) #= _v :- f(x) #= _v.
```

one might emit:

```asp
__aspf_value(h(x),V) :- __aspf_value(f(x),V).
```

This can reproduce the simple model relation, partiality, and functionality.
It does not preserve the source mechanism: `V` is an ordinary Clingo variable,
and the grounder instantiates the rule over every potential value tuple. The
additional grounded rules grow with the value domain. The historical source
rule is ground and does not have this growth.

### Fake symbolic placeholder

Replacing `_v` by a private constant such as `__aspf_nvar_v` prevents ordinary
grounding but compares the placeholder's identity with values instead of
assigning it a value. The copy rule then matches only an application whose
actual value is that private constant. This is semantically wrong.

### Inferred global value domain

Generating `__aspf_candidate(V)` from every source constant and joining through
it reintroduces the grounding expansion, admits unrelated constants, and makes
results sensitive to unrelated files. It also cannot represent solver-local
undefined n-variable state faithfully.

### Rule-local relational elimination

A structured compiler could eliminate some positive, acyclic n-variables by
sharing backend variables across relation lookups. This is useful as a semantic
experiment, but it remains an ordinary grounding translation. Multiple
definitions, arithmetic, default negation, n-loops, and solver-time undefined
states require a much larger proof. It therefore does not meet the historical
feature's operational contract or the release GO criteria.

## GO/NO-GO assessment

| Required property | Reference relation result |
| --- | --- |
| Grounder-inert source behavior | **Fail** — a shared backend variable is grounded over potential tuples |
| Binding through documented defining n-atoms | Partial for simple positive equality only |
| N-stratification | Could be validated syntactically, but validation alone does not implement values |
| Undefinedness | Partial for failed joins; no explicit rule-local n-variable state |
| Answer-set semantics | Unproved beyond simple positive elimination |
| No accidental ordinary-Clingo grounding | **Fail** |
| Reasonable historical grounding behavior | **Fail** — added ground rules grow with the value domain |

Decision: **NO-GO**. Do not add an n-variable IR node to the production frontend
and do not change its current location-aware rejection. The historical
compatibility case remains an intentional strict xfail.

## Research prototype

[`research/nvariable_reference_probe.py`](../../research/nvariable_reference_probe.py)
measures the candidate relation rewrite against a value-domain family. It
checks that the simple copy models agree, then shows that the number of
additional grounded rules grows with the domain. The script is evidence for
the NO-GO decision, not an alternate frontend.

## Required future backend

A credible implementation should use a separately reviewed theory/propagator
backend:

1. Add a distinct `NVariable` IR node only after exact lexical compatibility is
   fixed.
2. Build a rule-local definition graph and reject forbidden argument positions,
   missing positive definitions, and non-stratified cycles with source spans.
3. Lower n-atoms to Clingo theory atoms that retain n-variable identity without
   exposing it as an ordinary grounder variable.
4. Maintain thread-local application and n-variable value tables in a custom
   propagator, including explicit undefined states and undo on backtracking.
5. Propagate defining equalities in index order, evaluate arithmetic and body
   comparisons only from assigned values, and emit explained conflicts for
   functionality and inconsistent definitions.
6. Analyze program-level n-loops and state the exact compatibility restriction
   before claiming soundness/completeness.
7. Compare answer sets with primary-source examples and measure both grounding
   and solving behavior against the reference backend.

This design does not authorize arithmetic, aggregate, choice, or propagator
work in the current release.
