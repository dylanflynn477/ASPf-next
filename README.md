# aspf-next

`aspf-next` is an experimental, compatibility-first revival of Marcello
Balduccini's ASP{f} language on the public Python API of Clingo 5.8. ASP{f}
extends Answer Set Programming with partial non-Herbrand functions.

This is an **independent clean-room modernization**. Marcello Balduccini is the
creator of ASP{f} and its Clingo{f} implementation; this project is not the
historical implementation, does not copy its code, and does not claim full
ASP{f} compatibility. The original research is described in Balduccini's paper
[“ASP with non-Herbrand partial functions: a language and system for practical
use”](https://doi.org/10.1017/S1471068413000343).

This project is also distinct from Potassco's
[`flingo`](https://potassco.org/systems/), a solver for ASP with founded
conditional linear constraints. Similar names and support for undefined values
do not make the languages or implementations interchangeable.

## Milestone status

Version 0.1 is a deliberately narrow vertical slice. It supports:

- local declarations of the form `#nherb f/n.`;
- ground non-Herbrand applications, including zero-arity functions;
- `#=` assignments as facts and complete rule heads;
- positive `#=` comparisons as complete rule-body literals;
- integer, symbolic constant, and string values;
- ground integer, string, symbolic, and ordinary compound terms as application
  arguments;
- ordinary Clingo statements that contain no ASP{f} syntax in this slice;
- `%` line comments, `%* ... *%` block comments, multiline statements, quoted
  strings, and nested `()`, `[]`, and `{}` while scanning;
- bounded or complete model enumeration and normalized ASP{f}-style output.

It does **not** support:

- `#!=`, `#<`, `#<=`, `#>`, or `#>=`;
- default-negated n-atoms;
- variables of any kind inside n-atoms, including legacy non-Herbrand variables
  such as `_v`;
- arithmetic expressions inside n-atoms;
- aggregates or choice constructs containing n-atoms;
- a declared non-Herbrand application nested in another n-atom, whether as an
  argument or as a value;
- compound terms as assignment values (values are limited to integers, symbolic
  constants, and strings in this milestone);
- n-atoms embedded in disjunctions, conditional literals, or any position other
  than a complete assignment head/fact or positive body literal;
- global `#nherb.` declarations;
- legacy `#show #nherb` or `#hide #nherb` directives;
- arithmetic, aggregate, or choice-rule ASP{f} semantics from later milestones;
- native theory-atom or custom-propagator execution.

Unsupported or ambiguous ASP{f}-shaped syntax raises a location-aware
`UnsupportedSyntaxError` rather than receiving invented semantics. See
[`docs/supported-language.md`](docs/supported-language.md) for the precise
boundary.

## Installation

Python 3.11 or newer is required. From a checkout:

```console
python -m venv .venv
# POSIX:   source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

The runtime dependency is the official `clingo>=5.8,<5.9` Python package. The
development extra installs pytest, Ruff, and mypy.

## Run it

The basic example declares a partial function, assigns a value, and uses a
positive body comparison:

```asp
#nherb balance/1.

balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
```

```console
aspf examples/basic_assignment.aspf
```

Expected normalized output:

```text
Answer: 1
solvent(account1) balance(account1)#=500
SATISFIABLE
```

Enumerate all models by passing zero, just as with Clingo:

```console
aspf program.aspf --models 0
```

Inspect the ordinary Clingo reference translation without solving:

```console
aspf examples/basic_assignment.aspf --emit-lowered
```

Request machine-readable output:

```console
aspf examples/conditional_assignment.aspf --json
```

Multiple input files share one non-Herbrand declaration namespace:

```console
aspf declarations.aspf rules.aspf --models 0
```

## Reference backend

The initial backend lowers a supported assignment such as:

```asp
balance(account1) #= 500.
```

to an ordinary Clingo atom:

```asp
__aspf_value(balance(account1),500).
```

It also adds one functionality constraint:

```asp
:- __aspf_value(K,V1),
   __aspf_value(K,V2),
   V1 != V2.
```

No totality rule is added. If no internal value atom exists for an application,
that partial function application is undefined. Internal predicates are removed
from normal output and true value atoms are reconstructed as `f(args)#=value`.

This is a correctness-oriented **reference translation**, not a native
propagator and not a claim to the grounding-efficiency benefits of historical
Clingo{f}. A possible future theory-atom/custom-propagator backend is documented
as architecture only and is not implemented.

## Development

```console
ruff format --check src tests
ruff check src tests
mypy src
pytest
```

The package uses a `src` layout and keeps scanning, parsing/validation, IR,
lowering, solving, and model rendering in separate modules. Start with
[`docs/architecture.md`](docs/architecture.md) and
[`docs/provenance.md`](docs/provenance.md) before contributing compatibility
features.

## License

MIT. The license covers this clean-room implementation only; it does not imply
ownership of the ASP{f} language or historical Clingo{f} work.

