# Portfolio copy

## Short card version

ASPf-next is Dylan Flynn's independent clean-room modernization of Marcello
Balduccini's ASP{f} language. The pre-alpha Python CLI translates a deliberately
restricted set of partial non-Herbrand function declarations, assignments, and
positive comparisons into ordinary Clingo 5.8 programs, then reconstructs
readable ASP{f}-style models with explicit diagnostics for unsupported syntax.

## Full project version

ASPf-next explores how Marcello Balduccini's ASP{f} language can be approached
through a modern, maintainable Clingo integration. Dylan Flynn built the project
as an independent clean-room Python frontend: a location-aware scanner preserves
source context, the compatibility frontend validates a narrowly documented
slice, typed intermediate representations separate syntax from execution, and a
reference backend lowers supported non-Herbrand assignments to ordinary Clingo
5.8 atoms. The CLI solves programs,
enumerates models, exposes the translation for inspection, and reconstructs
stable ASP{f}-style human and JSON output. The repository includes focused
semantic-boundary tests, Python 3.11/3.12 CI, guided examples, and explicit
provenance documentation. Version 0.1.0-alpha is intentionally experimental. It
does not implement inequalities, arithmetic, variables inside n-atoms,
aggregates containing n-atoms, or a native propagator, and it does not claim
full historical compatibility or historical grounding efficiency. The result
is a tested research baseline for evaluating future compatibility work without
silently inventing language behavior.

## Technical highlights

- Location-aware scanning across comments, strings, multiline statements, and
  nested delimiters.
- Typed separation of compatibility parsing, ASP{f} IR, reference lowering,
  Clingo solving, and model normalization.
- Explicit functionality and partiality through an inspectable
  `__aspf_value/2` translation.
- Location-aware rejection for unsupported or ambiguous ASP{f}-shaped syntax.
- Automated examples and quality gates across Python 3.11 and 3.12.

## Interview explanation

ASP{f}, created by Marcello Balduccini, extends Answer Set Programming with
partial non-Herbrand functions—applications can have one value or be undefined.
I built ASPf-next as a clean-room modernization around Clingo 5.8's Python API.
The current pre-alpha validates a restricted syntax, lowers it to an inspectable
reference encoding, solves it, and reconstructs readable models. It is a
research baseline; richer operators and a native backend remain experimental
future work.

## Project facts

| Field | Value |
| --- | --- |
| Project name | ASPf-next |
| Repository | `dylanflynn477/ASPf-next` |
| Project status | Experimental pre-alpha research software |
| Primary language | Python |
| Key technologies | Clingo 5.8, typed IR, pytest, Ruff, mypy, GitHub Actions |
| Current release | Not yet published; `0.1.0-alpha` is prepared (`0.1.0a1` Python package version) |
| License | MIT |
| Suggested website tags | Answer Set Programming, logic programming, Python, research software |
| Suggested call to action | View the source and try the guided examples |

**Suggested repository description:** Experimental clean-room ASP{f}
compatibility frontend for Clingo 5.8, with a typed Python pipeline and
inspectable reference lowering.

**Suggested GitHub topics:** `answer-set-programming`, `asp`, `clingo`,
`logic-programming`, `non-herbrand-functions`, `programming-languages`, `python`,
`research-software`
