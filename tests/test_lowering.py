from __future__ import annotations

from aspf_next.frontend import parse_program
from aspf_next.lowering import FUNCTIONALITY_CONSTRAINT, lower_program


def lowered(source: str) -> str:
    return lower_program(parse_program(source)).source


def test_lowers_basic_assignment_and_functionality() -> None:
    result = lowered("#nherb balance/1.\nbalance(account1) #= 500.\n")

    assert "__aspf_value(balance(account1),500)." in result
    assert result.count(FUNCTIONALITY_CONSTRAINT) == 1


def test_lowers_positive_body_comparison() -> None:
    result = lowered(
        """#nherb balance/1.
balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
"""
    )

    assert "solvent(account1) :- __aspf_value(balance(account1),500)." in result


def test_lowers_conditional_assignment_in_rule_head() -> None:
    result = lowered(
        """#nherb status/1.
active(alice).
status(alice) #= employed :- active(alice).
"""
    )

    assert "__aspf_value(status(alice),employed) :- active(alice)." in result


def test_lowers_multiple_body_comparisons_without_global_replacement() -> None:
    result = lowered(
        """#nherb left/1.
#nherb right/1.
ok :- left(a) #= "#= literal", right(b) #= value.
"""
    )

    assert '__aspf_value(left(a),"#= literal")' in result
    assert "__aspf_value(right(b),value)" in result
    assert '"#= literal"' in result


def test_preserves_ordinary_program_exactly_without_declarations() -> None:
    source = '% untouched.\nmessage("#= is text").\np(X) :- q(X).\n'

    assert lowered(source) == source


def test_declaration_alone_adds_no_totality_rule() -> None:
    result = lowered("#nherb balance/1.\naccount(account1).\n")

    assert "account(account1)." in result
    assert "__aspf_value(K,V) :-" not in result
    assert result.count("__aspf_value") == 2
