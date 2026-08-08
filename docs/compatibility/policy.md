# Historical compatibility policy

ASPf-next is an independent clean-room project. Historical compatibility claims
must be tied to a named construct, an attributed source, an executable test,
and the observable behavior being compared. Parser acceptance alone is not
evidence of semantic compatibility.

## Compatibility dimensions

### Source compatible

A historical Clingo{f} program is source compatible for a named construct when
ASPf-next accepts the documented historical syntax without source edits.

### Semantically compatible

An accepted program is semantically compatible for a named subset when its
relevant answer-set behavior agrees with the documented ASP{f}/Clingo{f}
semantics. This includes partiality, functionality, definedness requirements,
and the distinction between Herbrand values and non-Herbrand applications.

### Output compatible

Output is compatible for a named subset when human-readable output preserves
the relevant visible ordinary atoms and reconstructed assignments, modulo
documented ordering, spacing, and status-line differences. Internal
`__aspf_` predicates are never part of the compatibility surface.

### CLI compatible

CLI compatibility means a historical command-line form works unchanged or has
an explicitly documented migration path. The current `aspf` CLI is not a
drop-in replacement for the historical `clingof` command line.

## Status vocabulary

- **Historically compatible**: source and relevant semantics for the named,
  attributed cases are covered by passing tests.
- **Historically compatible with restriction**: the tested overlap is
  semantically compatible, but ASPf-next accepts fewer source forms, value
  classes, or contexts.
- **ASPf-next extension/design choice**: behavior belongs to this clean-room
  frontend or backend and is not attributed to historical ASP{f}/Clingo{f}.
- **Not yet compatible**: the historical construct is valid but ASPf-next
  rejects it with a location-aware diagnostic or cannot yet establish faithful
  semantics.
- **Invalid historical program**: the cited historical source rejects the
  program too; a matching ASPf-next rejection is a passing compatibility case.
- **Unresolved**: primary-source interpretation or a faithful implementation
  decision has not yet been established. There are no unresolved cases in the
  current 39-case target.

Documentation should prefer precise phrases such as:

- "historical compatibility subset";
- "source-compatible for application-style declarations";
- "semantically compatible for the tested positive-comparison subset."

ASPf-next must not be called globally "backward compatible with Clingo{f}"
until a separately defined target is met.

## Evidence requirements

Every compatibility case records:

1. a stable identifier and minimal source fixture;
2. its primary-source origin;
3. expected historical validity and semantics;
4. baseline and current ASPf-next status;
5. a compatibility tier;
6. expected models when the result is reproducible; and
7. a passing, strict-xfail, or intentionally deferred disposition.

Strict unresolved xfails represent known work, not ignored failures. Deferred
unsupported cases assert an exact diagnostic before calling `pytest.xfail`, so
an unrelated exception cannot masquerade as expected incompatibility. If a
deferred feature begins parsing, the suite fails until its models, manifest,
and documentation are reviewed.

## Current compatibility target

The current executable target has 39 attributed cases: 35 matching cases,
including 7 restricted overlaps and 2 invalid historical programs that are
correctly rejected; 4 intentionally deferred unsupported cases; and no
unresolved cases.

The implemented target covers explicit, application-style, and global
declarations; partial functional assignments; scalar and application body
comparisons; definedness-aware default negation; ordinary declared-symbol
scope; visibility controls; and P1-P3 ordinary-variable safety including
positive seed-equality safety. Integer-only order, direct key variables,
complete value variables, body placement, and global zero-arity resolution are
documented restrictions.

Non-Herbrand variables, arithmetic, choices, and aggregates are intentionally
deferred. The n-variable case is a researched backend NO-GO, not unresolved.
Private predicates, namespace reservation, reference lowering, and normalized
output ordering are ASPf-next design choices.

## Clean-room rule

Compatibility research may use published papers and public documentation.
Historical Clingo{f} implementation source must not be copied, ported,
translated, or consulted as an implementation template.
