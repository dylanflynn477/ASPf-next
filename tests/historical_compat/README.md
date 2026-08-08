# Historical compatibility corpus

This suite is an attributed executable target for documented historical
Clingo{f} behavior. It is intentionally separate from `tests/conformance`,
which also records deliberate ASPf-next restrictions.

Run it with:

```console
pytest tests/historical_compat
python scripts/compatibility_report.py
```

Passing cases are regression contracts. Historically valid constructs that are
not implemented are strict xfails: an XPASS fails the suite until the manifest,
expected models, and compatibility documentation are reviewed.
