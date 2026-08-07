# Global `#nherb.` design

Status: researched and intentionally deferred from
`historical-compatibility-1`.

## Historical contract

The public Clingo{f} documentation states that `#nherb.` makes function
symbols interpreted by `#` connectives non-Herbrand without individual
declarations. It also states that occurrences outside n-atoms remain ordinary
Herbrand syntax. Its examples use both positive-arity applications and
zero-arity applications such as `p #= 1`.

## Required representation

Global mode must be a program-level declaration policy in the IR, not guessed
`#nherb f/n.` text inserted after scanning. Operand classification would then
be:

- left-side functional syntax under `#`: non-Herbrand application;
- positive-arity functional syntax on either side under `#`: non-Herbrand
  application in global mode;
- occurrences outside an n-atom: ordinary Clingo syntax;
- constants used as seed values: Herbrand constants.

Explicit declaration mode and global mode should be mutually clear in the IR,
including across multiple input files.

## Blocker

The historical surface uses the same lowercase token class for symbolic
constants and zero-arity function symbols. In explicit mode, `#nherb f/0.`
resolves this. In global mode, the frontend needs a source-backed rule for
classifying a bare right operand: for example, distinguishing a constant value
in `f(a) #= active` from a zero-arity application in a dependent comparison.
The public examples establish zero-arity left applications but do not fully
specify this right-operand ambiguity.

Treating every bare right symbol as an application would make ordinary symbolic
seed values impossible. Treating every bare right symbol as a constant would
make dependent comparisons to zero-arity applications impossible. Inferring a
global signature from use sites would add a whole-program semantic pass and
requires a documented conflict rule.

## Decision

Keep `#nherb.` as a strict historical xfail. A future milestone may implement
it after the right-operand signature rule is established from primary evidence
and represented explicitly. The implementation must preserve ordinary syntax
outside n-atoms and must not weaken the `__aspf_` namespace reservation.
