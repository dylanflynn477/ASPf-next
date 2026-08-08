# Portfolio demo: partial technical indicators

This synthetic example demonstrates missing-data semantics, not market
prediction. It produces no buy/sell recommendation and makes no claim that the
indicator has predictive value.

## The representation problem

A 14-observation indicator cannot be calculated for the first 13 observations.
That is different from calculating it and obtaining zero:

```text
undefined ≠ 0
```

[`technical_indicators.aspf`](../examples/portfolio/technical_indicators.aspf)
uses signed daily close changes in integer basis points. Their externally
calculated 14-observation simple moving average is represented by the partial
non-Herbrand function `sma14_delta/1`:

| Day | `sma14_delta` | Meaning |
| --- | ---: | --- |
| 1–13 | undefined | no complete 14-observation window |
| 14 | 0 | calculated; the 14 changes sum to zero |
| 15 | 1 | calculated; the moving average is one basis point |
| 16 | 0 | calculated; the current 14 changes sum to zero |

ASPf-next does not calculate this SMA internally; arithmetic in n-atoms is
intentionally unsupported. The fixture supplies small, coherent precomputed
values so the demo stays within the tested language boundary.

For a Python reader, the distinction resembles membership in a dictionary:

```python
sma14_delta = {14: 0, 15: 1, 16: 0}

assert 14 in sma14_delta and sma14_delta[14] == 0
assert 1 not in sma14_delta
```

An ASP{f} declaration does not create a total function. The absence of an
assignment is the undefined case; no distinguished `undefined` constant and no
default zero are inserted.

## Positive comparison requires defined values

The main rule compares the values of two partial applications:

```asp
above_average(D) :-
    day(D),
    price_delta(D) #> sma14_delta(D).
```

Both applications must have defined integer values. The rule derives
`above_average(15)` because `19 > 1`. It derives nothing for days 1–13 because
`sma14_delta(D)` is undefined there—not because an invented zero failed or
passed the comparison.

The companion rule makes the defined-zero cases observable:

```asp
zero_average(D) :-
    day(D),
    sma14_delta(D) #= 0.
```

It derives `zero_average(14)` and `zero_average(16)`. The same rule does not
derive anything for days 1–13, which shows that undefined and zero are not
conflated.

## Default negation means threshold failure

The second use case is a rules-oriented review queue:

```asp
needs_review(D) :-
    evaluated(D),
    not confidence(D) #>= 70.
```

Day 14 has defined confidence `80`, so the threshold is established and no
review is requested. Day 15 has defined confidence `45`, so positive
`confidence(15) #>= 70` is false and review is requested. Day 16 has no
confidence assignment, so the positive comparison is also unsatisfied and
review is requested.

Default negation is therefore not an “is undefined” operator. It says that the
positive threshold cannot be established. A defined below-threshold value and
an undefined value can both satisfy this rule for different underlying
reasons. A separate explicit definedness feature would be needed to distinguish
those reasons directly; this demo does not invent one.

## Run it

From an installed checkout:

```console
aspf examples/portfolio/technical_indicators.aspf --models 0
```

Expected output:

```text
Answer: 1
above_average(15) needs_review(15) needs_review(16) zero_average(14) zero_average(16) confidence(14)#=80 confidence(15)#=45 sma14_delta(14)#=0 sma14_delta(15)#=1 sma14_delta(16)#=0
SATISFIABLE
```

The `price_delta/1` assignments are hidden only from presentation to keep the
model readable; they remain present during solving. To inspect the reference
translation, run:

```console
aspf examples/portfolio/technical_indicators.aspf --emit-lowered
```

Use `--json` for structured model output. Private predicates beginning with
`__aspf_` appear only in intentional lowered output, never in normal human or
JSON models.
