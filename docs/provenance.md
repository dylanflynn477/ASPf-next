# Provenance and clean-room policy

## Attribution

Marcello Balduccini created ASP{f} and the historical Clingo{f} implementation.
The language's research context and partial non-Herbrand function semantics are
described in:

- Marcello Balduccini, [“ASP with non-Herbrand partial functions: a language and
  system for practical use”](https://doi.org/10.1017/S1471068413000343), TPLP
  13(4–5), 2013.
- Marcello Balduccini and Michael Gelfond, [“Language ASP{f} with Arithmetic
  Expressions and Consistency-Restoring Rules”](https://arxiv.org/abs/1301.1387),
  2013.

`aspf-next` is an independent modernization and is not endorsed by or affiliated
with Balduccini, the historical Clingo{f} project, or Potassco.

## Implementation provenance

The compatibility frontend and reference backend were written from the
milestone specifications in this repository, primary publications, and the
public interfaces of the official Clingo Python package. They do not fork,
patch, or modify Clingo's C/C++ source and do not copy code from historical
Clingo{f}.

The implementation intentionally separates compatibility scanning, typed IR,
reference lowering, solver integration, and output normalization. The internal
`__aspf_value/2` representation and functionality rule are an explicit reference
encoding for this milestone, not a reverse-engineered native implementation.

Relevant public Clingo interfaces:

- [Clingo 5.8 Python API](https://potassco.org/clingo/python-api/5.8/)
- [model symbol selection](https://potassco.org/clingo/python-api/5.8/clingo/solving.html)
- [theory atoms](https://potassco.org/clingo/python-api/5.8/clingo/theory_atoms.html)
- [custom propagators](https://potassco.org/clingo/python-api/5.8/clingo/propagator.html)

The latter two links now inform a bounded research prototype under
`research/native_backend/`. That prototype is not imported by the released
package, exposed by the CLI, or represented as production support. The
reference backend remains the default and supported implementation.

## Authorship and licensing record

The repository audit for the `0.2.0a2` release found commits and merged pull
requests authored only through Dylan Flynn's recorded name/email
identities and GitHub account, with no co-author trailers or other GitHub
contributors. No third-party implementation is vendored. Clingo remains an
external runtime dependency under its own terms.

That evidence is useful but is not a legal determination that every copyright
interest is owned by one person. The maintainer approved the transition after
the audit disclosed employment/contractor and tool-assisted-work questions.
External patches are paused until a reviewed contributor-agreement process exists. See
[`docs/licensing.md`](licensing.md).

## Distinction from Potassco flingo

Potassco lists `flingo` as a solver for ASP modulo founded conditional linear
constraints, and its published package describes a translation to `clingcon`.
That is a separate contemporary language and tool. `aspf-next` targets a
restricted compatibility path for ASP{f}'s historical surface syntax. Neither
name should be used as an alias for the other.

Primary references:

- [Potassco systems index](https://potassco.org/systems/)
- [Potassco flingo package](https://pypi.org/project/flingo/)

## Contribution rule

Contributions must remain clean-room:

1. Do not paste, port, translate, or mechanically reproduce historical Clingo{f}
   implementation code.
2. Cite public papers or documentation used to justify semantic behavior.
3. Record uncertain historical behavior as an open semantic question.
4. Add a location-aware rejection before accepting syntax whose semantics are
   not specified and tested.
5. Keep native backend experiments separate from the reference backend and test
   them for answer-set equivalence on the supported slice.
