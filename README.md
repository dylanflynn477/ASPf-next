# ASPf-next

[![CI](https://github.com/dylanflynn477/ASPf-next/actions/workflows/ci.yml/badge.svg)](https://github.com/dylanflynn477/ASPf-next/actions/workflows/ci.yml)
[![Python 3.11–3.12](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](docs/roadmap.md)

ASPf-next is an experimental, independent clean-room modernization of Marcello
Balduccini's ASP{f} language. It provides a compatibility frontend for modern
Clingo 5.8, bringing partial non-Herbrand function notation to a tested Python
CLI while keeping milestone 0.1's semantic boundary deliberately narrow.

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

Continue with the [five guided examples](examples/README.md) or the
[step-by-step quickstart](docs/quickstart.md). The examples include partiality,
a conditional assignment, a conflicting-value program, and ordinary ASP model
enumeration.

## What milestone 0.1 can do

The implemented slice supports:

- `#nherb f/n.` declarations, including zero-arity functions;
- ground function applications and `#=` assignments as facts or complete rule
  heads;
- positive, ground `#=` comparisons as complete rule-body literals;
- integer, symbolic constant, and string values;
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

Milestone 0.1 deliberately rejects:

- `#!=`, `#<`, `#<=`, `#>`, and `#>=`;
- default-negated n-atoms;
- variables, including `_v` non-Herbrand variables, inside n-atoms;
- arithmetic expressions inside n-atoms;
- aggregates, choices, disjunctions, or conditional literals containing
  n-atoms;
- compound assignment values and nested declared non-Herbrand applications;
- global `#nherb.` and legacy `#show #nherb` / `#hide #nherb` directives;
- declared non-Herbrand symbols anywhere except the key of a supported n-atom;
  and
- user-written executable identifiers beginning with the reserved `__aspf_`
  prefix.

Unsupported or ambiguous ASP{f}-shaped syntax raises a filename-, line-, and
column-aware `UnsupportedSyntaxError` instead of receiving invented semantics.
There is no native theory-atom backend, custom propagator, arithmetic extension,
optimization layer, or historical conformance claim in this release.

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
- [Semantics notes](docs/semantics-notes.md)
- [Architecture](docs/architecture.md)
- [Provenance and clean-room policy](docs/provenance.md)
- [Roadmap](docs/roadmap.md)
- [0.1.0-alpha release notes](docs/releases/0.1.0-alpha.md)

## Roadmap and status

The codebase is prepared for `0.1.0-alpha` (Python package version `0.1.0a1`),
but that release has not been published. This remains pre-alpha research
software. The [roadmap](docs/roadmap.md) separates the shipped reference
frontend from possible 0.2 compatibility work and longer-term native-backend
research. Those directions are proposals, not promises.

## Development and attribution

```console
ruff format --check src tests
ruff check src tests
mypy src
pytest
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
