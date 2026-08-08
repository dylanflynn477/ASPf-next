# Historical seed-equality safety

Status: reference-backend design approved with the restrictions below.

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

The distinction is source-level safety, not procedural unification. A positive
seed equality can provide safe occurrences for ordinary variables. A dependent
n-atom follows the same safety restriction as a default-negated literal. B13
also makes ordinary grounder variables and grounder-inert non-Herbrand
variables separate mechanisms.

## Typed distinction

The compatibility frontend must keep four categories distinct:

1. `VariableTerm` is an ordinary source variable used directly as an
   application argument.
2. `ValueVariableOperand` is an ordinary source variable occupying the entire
   right operand of a body n-atom.
3. `ApplicationOperand` is a declared non-Herbrand application whose value is
   read by a dependent comparison.
4. A future non-Herbrand variable such as `_v` is neither of the ordinary
   variable nodes above. It remains unsupported and must never reach Clingo as
   an ordinary variable.

A ground scalar, compound Herbrand scalar, application operand, and ordinary
value variable therefore remain explicit alternatives in the IR.

## Exact source-safety rule

The following body literal is a **seed-equality safety provider**:

```text
positive, non-default-negated application #= ordinary-value-variable
```

Such a literal provides safe occurrences for its direct application-argument
variables and its right value variable. The safety information is rule-local
and may be shared with other literals in the same rule.

These forms do not provide safety:

- application-to-application `#=`;
- `#!=`;
- `#<`, `#<=`, `#>`, or `#>=`;
- any default-negated n-atom;
- any assignment in a rule head.

Variables in those forms must occur in an ordinary positive symbolic body atom
or in a positive seed-equality provider in the same rule. This preserves the
historical rejection of P4 and P5 instead of allowing generated backend
lookups to legalize them accidentally.

Value variables in equality and inequality are supported when this rule makes
them safe. Ordered comparisons with a value-variable operand remain rejected:
an ordinary symbolic domain does not prove that all of its values are integers,
and raw Clingo term order is not ASP{f} numeric order. Value variables in rule
heads remain outside this increment.

## Reference lowering

A supported positive seed equality lowers directly through the value relation:

```asp
p(X,Y) :- l(X) #= Y.
```

```asp
p(X,Y) :- __aspf_value(l(X),Y).
```

No separate inferred value domain is generated.

This translation has the required semantic properties for the restricted
grammar:

- **Grounding domain.** `Y` ranges over the second components of potentially
  supported `__aspf_value/2` tuples for matching keys, and `X` ranges over their
  key arguments. Unrelated constants do not enter either position merely
  because they occur elsewhere.
- **Partiality.** With no matching value tuple, the positive lookup fails. No
  rule invents a value and no totality rule is added.
- **Functionality.** The existing global constraint still excludes two
  different values for one key.
- **Conditional and multiple-model assignments.** The grounder sees the
  potential relation tuples produced by assignment heads. Solving then derives
  `p(X,Y)` only for tuples present in each model.
- **Positive recursion.** A value tuple obtained through a supported recursive
  assignment can feed the same positive join. A positive cycle with no base
  assignment produces no tuple, matching partiality rather than creating a
  synthetic domain.
- **Multiple files.** Parsing already builds one whole-program declaration and
  signature policy, while lowering concatenates statements into one program.
  The join does not depend on file order.
- **Value kinds.** Because the lookup binds an ordinary Clingo term, it carries
  the already-supported integer, symbolic, string, and compound Herbrand values
  without enumerating a global universe.

The analysis was checked with empty P1, fact-backed P2, unrelated constants,
conditional assignments across two models, recursive assignments with a base,
and a positive recursive cycle without a base. The production conformance
corpus records these obligations.

This is a correctness-oriented reference translation. It does not reproduce or
claim the grounding-efficiency advantages of historical Clingo{f}.

## Lowering other value-variable comparisons

An independently safe inequality such as:

```asp
value(Y).
different :- value(Y), l(a) #!= Y.
```

uses a fresh backend value lookup followed by ordinary Herbrand inequality:

```asp
different :-
    value(Y),
    __aspf_value(l(a),_AspfNeq0),
    _AspfNeq0 != Y.
```

The private lookup preserves definedness. The source `#!=` literal supplies no
safety itself. A default-negated equality with independently safe variables can
reuse the existing positive-satisfaction helper, including the value variable
in the helper key.

Ordered value-variable comparisons are not lowered because the current private
integer predicate describes known assignment values, not arbitrary values from
ordinary user predicates. Accepting such a comparison would risk delegating
numeric order to Clingo's generic term order.

## Decision

**GO with a narrow grammar.** Add a typed ordinary value-variable operand and
allow positive seed equality to establish rule-local safety exactly as above.
Keep dependent comparisons and default negation non-binding, keep `_v`
non-Herbrand variables distinct and unsupported, and do not add an inferred
value domain.
