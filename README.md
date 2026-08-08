# ASPf-next

[![CI](https://github.com/dylanflynn477/ASPf-next/actions/workflows/ci.yml/badge.svg)](https://github.com/dylanflynn477/ASPf-next/actions/workflows/ci.yml)
[![Python 3.11–3.12](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](docs/roadmap.md)

ASPf-next is an experimental, independent clean-room modernization of Marcello
Balduccini's ASP{f} language. It provides a compatibility frontend for modern
Clingo 5.8, bringing partial non-Herbrand function notation to a tested Python
CLI while keeping its semantic boundary deliberately narrow.

## What is ASP{f}?

Answer Set Programming (ASP) describes a problem as logical rules and asks a
solver to find models that satisfy them. ASP{f} extends that style with partial
non-Herbrand functions: an application such as `balance(account1)` can have one
value, or it can be undefined.

```asp
#nherb balance/1.
balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
```

Marcello Balduccini created ASP{f} and the historical Clingo{f}
implementation. ASPf-next exists to explore a maintainable compatibility path
on Clingo's supported Python API. It is not the historical implementation,
does not copy its code, and does not claim full ASP{f} compatibility.

## Try it in under two minutes

Python 3.11 or newer is required; CI currently tests 3.11 and 3.12. From a
checkout:

```console
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows:     .venv\Scripts\activate
python -m pip install -e ".[dev]"
aspf examples/01_basic_assignment.aspf
```

Expected output:

```text
Answer: 1
solvent(account1) balance(account1)#=500
SATISFIABLE
```

Continue with the [nine guided examples](examples/README.md) or the
[step-by-step quickstart](docs/quickstart.md). The examples include partiality,
a conditional assignment, a conflicting-value program, ordered integer
comparisons, application-to-application comparisons, historically compatible
default negation, and ordinary ASP model enumeration.

## What the current implementation can do

The implemented slice supports:

- `#nherb f/n.` declarations, including zero-arity functions, plus historical
  application-style declarations such as `#nherb f(X).`;
- historical global `#nherb.` mode for functional expressions under `#`, with
  ordinary occurrences outside n-atoms left unchanged;
- the same declared name at multiple arities, identified by exact `name/arity`;
- function applications and `#=` assignments as facts or complete rule heads;
- positive `#=` and `#!=` comparisons as complete rule-body literals, with
  defined-value semantics;
- positive `#<`, `#<=`, `#>`, and `#>=` body comparisons against integer
  literals, requiring a defined integer application value;
- positive body comparisons between two declared non-Herbrand applications for
  all six operators; equality and inequality require two defined values, while
  ordering additionally requires two integer values;
- one `not` before any otherwise supported complete body comparison. It is true
  when the positive n-atom is not satisfied, including when either required
  application value is undefined;
- ordinary uppercase variables as direct application arguments when every such
  variable also occurs in an ordinary, unnegated positive body atom in the same
  rule;
- integer, symbolic constant, string, and ground undeclared compound Herbrand
  values;
- scope-sensitive functional operands: an exact declared `name/arity` under a
  `#` connective is an application, while an undeclared ground function term is
  a Herbrand value; in global mode, positive-arity right functional expressions
  are applications, and zero-arity right applications use the program's
  explicit or key-established signature;
- ordinary Clingo statements that do not contain ASP{f} syntax in this slice;
- `%` and `%* ... *%` comments, quoted strings, multiline statements, and
  context-aware scanning of nested delimiters;
- bounded or complete model enumeration; and
- stable human-readable and JSON output with internal predicates hidden.

The precise, normative boundary is in
[`docs/supported-language.md`](docs/supported-language.md), with a compact view
in the [compatibility matrix](docs/compatibility-matrix.md).

## How it works

ASPf-next validates the supported legacy notation, records typed ASP{f} IR, and
applies an inspectable **reference translation**. For example:

```asp
balance(account1) #= 500.
```

becomes ordinary Clingo input equivalent to:

```asp
__aspf_value(balance(account1),500).
```

The backend adds a functionality constraint so the same ground application
cannot have two distinct values. It adds no totality rule: an absent value atom
means the application is undefined. Models are then normalized back to notation
such as `balance(account1)#=500`, without exposing the private `__aspf_`
predicates in normal output.

Default negation names the satisfaction of the positive comparison with a
fresh private helper and negates that helper. For example, `not f(a) #!= 1` is
true when `f(a)` equals `1` and when `f(a)` is undefined; it is never rewritten
as positive equality. Helpers are parameterized by the source variables in the
comparison, so different ground keys cannot be mixed. They remain visible only
in intentional `--emit-lowered` output.

A supported body inequality first looks up the application's value and then
compares it with the right operand. For example,
`different :- balance(account1) #!= 600.` succeeds only when
`balance(account1)` has a defined value other than `600`. It is false when the
application is undefined; `#!=` is never interpreted as the absence of `#=`.

Direct key arguments may use independently domain-safe ordinary variables. For
example, `low(A) :- account(A), balance(A) #< 1000.` is accepted because
`account(A)` supplies `A`'s source-level grounding domain. The generated private
lookup never supplies that safety. A scalar right operand remains ground; a
declared application right operand may use variables that independently satisfy
the same source-level rule.

Application-to-application equality and inequality compare values rather than
key syntax. Both lookups must succeed, so two undefined applications are neither
equal nor unequal. Application equality is a dependent body comparison, not a
copy assignment, and is rejected in a rule head.

Ordered comparisons follow the same defined-value discipline but are numeric
only. The reference backend records which assignment values are integer
literals, requires that marker during lookup, and then applies the corresponding
ordinary Clingo comparison. Symbolic constants and strings are never coerced or
exposed to Clingo's general term ordering.

A declaration changes functional-term interpretation only within a supported
n-atom. Outside `#` connectives, the same spelling keeps its ordinary Herbrand
meaning. Thus `ordinary(k(1))` remains exactly that atom even when `k/1` is
declared and `k(1) #= 5` also holds.

```text
ASP{f} source → scanner → validation → typed IR → reference lowering
               → Clingo 5.8 → normalized ASP{f}-style output
```

See the [architecture document](docs/architecture.md) for the full Mermaid
diagram and component boundaries. This backend is a correctness-oriented
reference translation, not a native solver extension and not a claim to the
grounding-efficiency behavior of historical Clingo{f}.

Inspect the translation directly:

```console
aspf examples/01_basic_assignment.aspf --emit-lowered
```

Request machine-readable results:

```console
aspf examples/03_conditional_assignment.aspf --json
```

Enumerate every model with `--models 0`:

```console
aspf examples/05_multiple_models.aspf --models 0
```

## Current limitations

The current implementation deliberately rejects:

- comparisons other than `#=` in rule heads, and n-atoms anywhere except a
  complete positive or singly default-negated body literal;
- non-integer scalar right operands for `#<`, `#<=`, `#>`, and `#>=`;
- double default negation and negated assignment heads;
- variables as n-atom values, variables nested inside application arguments,
  anonymous variables, and variables without an ordinary positive body domain;
- `_v` non-Herbrand variables in every n-atom position;
- arithmetic expressions inside n-atoms;
- aggregates, choices, disjunctions, or conditional literals containing
  n-atoms;
- declared non-Herbrand applications nested inside another n-atom operand;
- legacy `#show #nherb` / `#hide #nherb` directives;
- user-written executable identifiers beginning with the reserved `__aspf_`
  prefix.

Unsupported or ambiguous ASP{f}-shaped syntax raises a filename-, line-, and
column-aware `UnsupportedSyntaxError` instead of receiving invented semantics.
There is no native theory-atom backend, custom propagator, arithmetic extension,
optimization layer, or historical conformance claim in this release.

## Historical Clingo{f} compatibility

ASPf-next maintains an executable compatibility suite derived from documented
historical Clingo{f} behavior. Compatibility is currently provided for the
subset listed in the
[historical audit](docs/compatibility/historical-clingof-audit.md), including
explicit and application-style declarations, exact name/arity identity,
ordinary declared-symbol use outside n-atoms, and declared versus undeclared
ground functional operands. It also includes global `#nherb.` with a documented
zero-arity signature restriction, default-negated equality,
inequality, integer ordering, application operands, and independently
domain-safe key variables, with historical partiality behavior.

This is a historical compatibility subset, not a blanket backward-compatibility
claim. Legacy non-Herbrand visibility, historical equality-provided safety,
choices, aggregates, arithmetic, and non-Herbrand variables remain explicit
strict xfails or unresolved cases.

Run the corpus and its manifest-derived report with:

```console
pytest tests/historical_compat
python scripts/compatibility_report.py
```

The precise terminology is defined in the
[compatibility policy](docs/compatibility/policy.md). Runnable historically
styled programs are under [`examples/historical/`](examples/historical/).

## ASPf-next is not Flingo

ASPf-next and Potassco's
[`flingo`](https://potassco.org/systems/) are separate projects. Flingo targets
ASP with founded conditional linear constraints; ASPf-next targets a restricted
compatibility frontend for ASP{f}'s historical surface notation. Similar names
and support for undefined values do not make their languages or implementations
interchangeable. ASPf-next is not affiliated with Potassco.

## Documentation

- [Quickstart](docs/quickstart.md)
- [Guided examples](examples/README.md)
- [Supported language](docs/supported-language.md)
- [Compatibility matrix](docs/compatibility-matrix.md)
- [Historical compatibility audit](docs/compatibility/historical-clingof-audit.md)
- [Historical compatibility policy](docs/compatibility/policy.md)
- [Semantics notes](docs/semantics-notes.md)
- [Specification traceability](docs/specification-traceability.md)
- [Architecture decision records](docs/decisions/)
- [Architecture](docs/architecture.md)
- [Provenance and clean-room policy](docs/provenance.md)
- [Roadmap](docs/roadmap.md)
- [0.1.0-alpha release notes](docs/releases/0.1.0-alpha.md)
- [`#!=` development notes](docs/releases/not-equal-development.md)
- [ordered-comparison development notes](docs/releases/ordered-comparisons-development.md)
- [domain-safe variable development notes](docs/releases/domain-safe-variables-development.md)
- [variable semantics research](docs/design/variable-semantics.md)
- [restricted variable milestone plan](docs/design/variable-milestone-plan.md)
- [application operand semantics](docs/design/application-operands.md)

## Roadmap and status

The package metadata remains `0.1.0a1`, and that release has not been
published. The current comparison and restricted-variable work is unreleased development
and has not been assigned a release number. This remains pre-alpha research
software. The [roadmap](docs/roadmap.md) separates implemented reference
frontend work from later compatibility candidates and longer-term
native-backend research. Those directions are proposals, not promises.

## Development and attribution

```console
ruff format --check src tests
ruff check src tests
mypy src
pytest
pytest tests/conformance
pytest tests/historical_compat
python scripts/compatibility_report.py
```

Contributions must follow the [clean-room contribution guide](CONTRIBUTING.md).
The original research is described in Marcello Balduccini's paper,
[“ASP with non-Herbrand partial functions: a language and system for practical
use”](https://doi.org/10.1017/S1471068413000343). Detailed attribution and
implementation provenance are recorded in [`docs/provenance.md`](docs/provenance.md).

ASPf-next is independently created and maintained by Dylan Flynn. It is not
endorsed by or affiliated with Marcello Balduccini, the historical Clingo{f}
project, or Potassco.

## License

[MIT](LICENSE). The license covers this clean-room implementation only; it does
not imply ownership of ASP{f} or the historical Clingo{f} work.
