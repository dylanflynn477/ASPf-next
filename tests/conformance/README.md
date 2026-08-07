# Conformance corpus

`manifest.json` is the executable index for milestone 0.1 and subsequent
restricted compatibility-increment conformance cases.
Each case names one or more source files and records:

- whether parsing is accepted or rejected;
- solve status and model count for accepted deterministic programs;
- stable ordinary atoms and reconstructed assignments;
- the expected source-aware diagnostic for rejected programs; and
- whether the case is based on historical ASP{f} behavior or an ASPf-next
  project boundary.

The fixture directories group cases by the behavior they establish. Every
`.aspf` fixture must be referenced exactly once by the manifest. Run only this
corpus with:

```console
pytest tests/conformance
```

The source keys and precise locations used in `source_basis` are defined in the
[specification traceability document](../../docs/specification-traceability.md).
Adding a fixture without an explicit basis is a schema test failure.
