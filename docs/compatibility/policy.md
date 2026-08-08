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

- **Compatible**: source and relevant semantics are both covered by passing
  attributed tests.
- **Compatible with restriction**: the tested overlap is semantically
  compatible, but ASPf-next accepts fewer source forms or contexts.
- **Incompatible**: ASPf-next accepts or interprets the construct differently
  in a relevant observable way.
- **Unsupported**: ASPf-next rejects the construct with a location-aware
  diagnostic.
- **Unresolved**: primary-source interpretation or a faithful reference
  lowering has not yet been established.

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

Strict xfails represent known work, not ignored failures. An XPASS fails the
historical suite so the manifest and documentation must be reviewed before the
new behavior is counted as compatible.

## Current compatibility target

The implemented compatibility increments target documented explicit declarations,
positive ground seed assignments, positive dependent comparisons in supported
body positions, scope-sensitive declared/undeclared functional operands, and
ordinary use of declared symbols outside n-atoms. It retains ASPf-next's
integer-only ordering and conservative ordinary-variable safety restrictions.
One `not` before an otherwise supported body comparison follows historical
failure-of-positive-satisfaction semantics. Global declaration mode is included
with the documented zero-arity key-signature restriction. Historical
non-Herbrand visibility is included as presentation policy.

Historical equality-provided safety, non-Herbrand variables, arithmetic,
choices, and aggregates are visible deferred cases rather than part of this
target.

## Clean-room rule

Compatibility research may use published papers and public documentation.
Historical Clingo{f} implementation source must not be copied, ported,
translated, or consulted as an implementation template.
