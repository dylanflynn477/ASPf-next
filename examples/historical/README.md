# Historically styled runnable examples

These examples reproduce small public-documentation concepts without using
historical implementation code. They run unchanged in the current ASPf-next
historical compatibility subset.

| File | Construct and source basis | Syntax | Expected ASPf-next output |
| --- | --- | --- | --- |
| `alternative-declaration.aspf` | `#nherb f(X).` from Clingo{f} public Syntax documentation | Unchanged | `f(a)#=2` |
| `compound-herbrand-value.aspf` | Undeclared `k(1)` as a Herbrand value from Clingo{f} public Syntax documentation | Unchanged | `same f(a)#=k(1)` |
| `ordinary-declared-symbol.aspf` | Declared symbols retain ordinary meaning outside n-atoms, from Clingo{f} public Syntax documentation and B13 section 3 | Unchanged | `ordinary(k(1)) k(1)#=5` |
| `multiple-arities.aspf` | Exact name/arity declaration identity from B13 section 3 | Unchanged | `f(a)#=one f(a,b)#=two` |

Run one with:

```console
aspf examples/historical/compound-herbrand-value.aspf
```

ASPf-next sorts ordinary shown atoms before reconstructed assignments and uses
its own status lines. Those formatting details need not match historical
Clingo{f}; the relevant atoms and assignments do.
