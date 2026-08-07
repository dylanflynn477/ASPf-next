# Historical seed-equality safety

Status: researched and intentionally deferred from
`historical-compatibility-1`.

## Historical evidence

The public Clingo{f} syntax documentation labels these analogous programs
syntactically correct:

```asp
% P1
p(X,Y) :- l(X) #= Y.

% P2
l(a) #= 3.
p(X,Y) :- l(X) #= Y.
```

It labels the following patterns incorrect:

```asp
% P4
l(a) #= 3.
p(X) :- l(X) #!= 2.

% P5
l(a) #= 3.
p(X,Y) :- l(X) #!= Y.
```

The distinction is that positive seed equality can provide safety, while a
dependent literal follows safety restrictions analogous to default-negated
literals. B13 also explains that ordinary grounding and specialized
non-Herbrand variables are separate mechanisms.

## Reference-lowering analysis

A tempting P2 lowering is:

```asp
__aspf_value(l(a),3).
p(X,Y) :- __aspf_value(l(X),Y).
```

This is syntactically safe for modern Clingo because the positive private
relation binds both variables. It produces `p(a,3)` for this finite fact. That
observation is necessary but not sufficient for a general compatibility
claim.

Questions that must be resolved for the supported source grammar include:

1. Which finite key and value domains are available when assignments are
   conditional, recursive, or distributed across files?
2. Does allowing a private intensional predicate to establish safety generate
   exactly the historical ground instances, or merely the same model in simple
   examples?
3. How should application/application equality bind variables on each side?
4. Can a value variable range over compound Herbrand values without an explicit
   source value-domain construction?
5. Does positive recursion through `__aspf_value/2` alter grounding size or
   eliminate ground instances that historical Clingo{f} generated?

Partiality itself is represented correctly by relation absence, but it does not
answer these grounding questions.

## Decision

ASPf-next keeps its stricter rule: every ordinary variable inside an
application key needs an independent ordinary, unnegated positive symbolic body
atom, and scalar right operands remain ground. P1/P2 are strict unresolved
xfails; P4/P5 remain passing rejection tests.

A future compatibility slice should first define a restricted equality-safety
grammar, compare grounded reference programs for conditional and recursive
cases, and decide whether an explicit value-domain IR is required. Merely
removing the source-safety validator is not acceptable.
