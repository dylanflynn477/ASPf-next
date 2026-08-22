# Historical n-loops and the research detector

This note records the semantic boundary used by the isolated native-backend
experiment. It is a clean-room reading of the published ASP{f} definitions, not a
reconstruction of historical implementation code.

## Published criterion

Balduccini distinguishes a *simple term* such as `f(a)` from a seed n-atom such as
`f(a) #= 2`. An n-atom whose right side is not a constant is dependent. A rule head is
a seed literal, while its positive body may contain ordinary literals, seed n-atoms,
or dependent n-atoms. Default-negated literals are outside the positive body.

For a ground program, an n-loop exists for a seed n-atom `l` when the program's
dependency graph contains a nonempty positive path from `l` to an n-atom `l'`, and
`l` and `l'` contain a common simple term. The published minimal example is
conceptually `f #= 2 :- f #!= 3.` The 2012 result characterizes answer sets using the
solver's dependent-literal nogoods for t-loop-free programs; the 2013 Clingo{f}
account states the corresponding soundness/completeness scope for programs without
such positive paths.

Sources:

- [Balduccini, “An Answer Set Solver for non-Herbrand Programs: Progress Report,”
  NMR 2012, pp. 3 and 7](https://mbal.asklab.net/papers/bal12c.pdf)
- [Balduccini, “ASP with non-Herbrand Partial Functions: a Language and System for
  Practical Use,” TPLP 2013, pp. 5–8](https://mbal.asklab.net/papers/bal13.pdf)

## N-stratification is a different condition

An n-variable is a ground expression that is not replaced during ordinary grounding.
Each rule using one must contain a positive defining n-atom, the n-variable may not be
an argument of a simple or aggregate term, and the rule must admit an index assignment
in which each defined n-variable has greater index than the expression defining it.
Those checks order definitions *within one rule*. N-loop freedom is a program-level
condition over positive dependency paths. Passing one condition does not imply the
other.

For example, `_v #= f` can define `_v` without a rule-local definition cycle, while
the following rule still has a program-level n-loop because its head and positive
definition contain the same simple term `f`:

```asp
f #= _v :- _v #= f.
```

## Minimal graph examples

No n-loop: the positive dependency goes from a seed for `h` to an n-atom containing
`f`; no simple term is shared by the endpoints.

```asp
h #= _v :- _v #= f.
```

Direct n-loop:

```asp
f #= 2 :- f #!= 3.
```

Indirect n-loop through an ordinary literal:

```asp
f #= 2 :- p.
p :- f #!= 3.
```

Ordinary ASP recursion is not an n-loop because there is no n-atom endpoint and no
shared simple term:

```asp
p :- q.
q :- p.
```

A default-negated n-atom contributes no positive dependency edge, so this is not an
n-loop under the published criterion:

```asp
f #= 2 :- not f #!= 3.
```

## Detector contract

`research/native_backend/nloops.py` builds explicit literal-occurrence nodes and two
edge types:

- `positive-body` connects a rule head to each positive body literal;
- `literal-match` connects occurrences that denote the same variable-free literal or
  may unify after ordinary grounding.

Literal-match edges represent vertex identity and do not by themselves make a path
positive or nonempty. Traversal is deterministic, retains the rule identifier and
source location on nodes and edges, and reports a concrete path plus the shared simple
term.

The detector is exact for the variable-free research subfragment in which assignment
heads have constant values. It compares complete application keys, so `f(a)` and
`f(b)` are distinct simple terms even though they share a function symbol. It ignores
default-negated comparisons and follows ordinary literals across rules, addressing
both major defects of the earlier function-symbol cycle screen.

For non-ground patterns, matching performs rule-scoped first-order unification. It
therefore preserves repeated-variable constraints (`p(X,X)` cannot match `p(a,b)`) and
shares an ordinary-variable binding between an n-atom application key and its scalar
value. This removes two concrete conservative false-positive families without
enumerating a value domain.

The detector remains deliberately conservative when ordinary variables or dynamic
n-variable assignment-head values require reasoning about complete grounded joins.
Compatible paths can still exist syntactically when no actual grounding realizes all
of them together. This is a stated research restriction, not a claim of exact
historical detection for every non-ground ASP{f} program. Exact analysis of that wider
class should operate on grounded typed metadata while mapping each witness back to its
source rule.
