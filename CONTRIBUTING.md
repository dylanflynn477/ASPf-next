# Contributing

ASPf-next is research software with a deliberately conservative compatibility
boundary. Contributions are welcome when they keep that boundary explicit and
reviewable.

## Clean-room requirements

- Do not copy, port, translate, or mechanically reproduce historical Clingo{f}
  source code.
- Base semantic claims on primary papers or public official documentation, and
  cite the source in the relevant design or provenance document.
- Record uncertain behavior as an open question. Unsupported constructs should
  fail with a location-aware diagnostic rather than acquire invented semantics.
- Keep changes to scanning, IR, lowering, solving, and model rendering separated
  when practical.
- Every compatibility feature requires focused frontend, lowering, solver, CLI,
  and documentation coverage appropriate to the change.

See [`docs/provenance.md`](docs/provenance.md) before proposing semantic work.

## Development setup

```console
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows:     .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Run the full gate before opening a pull request:

```console
ruff format --check src tests
ruff check src tests
mypy src
pytest
```

## Pull requests

Keep pull requests narrow and explain:

1. the user-visible behavior being changed;
2. the semantic or documentation source supporting it;
3. the tests that establish the boundary; and
4. any syntax deliberately left unsupported.

Documentation and examples should use only programs accepted by the current
frontend. Do not bundle native-backend experiments with reference-backend fixes.
