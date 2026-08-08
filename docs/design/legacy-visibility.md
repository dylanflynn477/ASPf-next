# Legacy non-Herbrand visibility design

Status: researched and intentionally deferred from
`historical-compatibility-1`.

## Historical contract

The public Clingo{f} documentation defines:

```asp
#hide #nherb.
#hide #nherb f/1.
#show #nherb f/1.
```

The selected forms also have application-style spellings such as
`#show #nherb f(X).`. These directives change displayed seed assignments, not
the truth of rules or the answer sets. Historical ordinary `#hide.` also hides
seed assignments.

## ASPf-next design

Visibility belongs in a typed output policy carried by `Program` into model
normalization:

```text
ordinary Clingo #show policy -> ordinary shown atoms
ASPf assignment policy       -> reconstructed assignments
private __aspf_ atoms         -> always hidden
```

The assignment policy needs ordered handling of:

- default visibility;
- hide all assignments;
- hide a selected `(name, arity)`;
- show a selected `(name, arity)` after a broader hide;
- application-style arity inference; and
- multiple input files.

Lowering must remove legacy directives before modern Clingo parses them, but it
must not add rules or constraints for visibility.

## Why this branch defers it

The current `Program` contains declarations and statements but no output-policy
IR, and `normalize_model` receives only a Clingo model. Adding syntax acceptance
without carrying the policy through solving would be source-compatible but
output-incompatible. Passing directives through to modern Clingo would be both
version-dependent and semantically wrong.

Strict historical xfails cover hide-all and selective-show cases. A future
implementation should add dedicated frontend, IR, solver, model, human CLI, and
JSON tests before those cases become passing.
