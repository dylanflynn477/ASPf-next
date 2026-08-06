from __future__ import annotations

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program
from aspf_next.solver import SolveStatus, solve_program


def solve(source: str, *, models: int = 1):  # type: ignore[no-untyped-def]
    return solve_program(parse_program(source), models=models)


def test_basic_assignment_is_reconstructed() -> None:
    result = solve("#nherb balance/1.\nbalance(account1) #= 500.\n")

    assert result.status is SolveStatus.SATISFIABLE
    assert result.models[0].atoms == ("balance(account1)#=500",)


def test_positive_body_comparison_derives_ordinary_atom() -> None:
    result = solve(
        """#nherb balance/1.
balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
"""
    )

    assert result.models[0].ordinary_atoms == ("solvent(account1)",)
    assert result.models[0].assignments == ("balance(account1)#=500",)
    assert result.models[0].render() == "solvent(account1) balance(account1)#=500"


def test_conditional_assignment() -> None:
    result = solve(
        """#nherb status/1.
active(alice).
status(alice) #= employed :- active(alice).
"""
    )

    assert result.models[0].atoms == ("active(alice)", "status(alice)#=employed")


def test_conflicting_values_are_unsatisfiable() -> None:
    result = solve(
        """#nherb balance/1.
balance(account1) #= 500.
balance(account1) #= 600.
"""
    )

    assert result.status is SolveStatus.UNSATISFIABLE
    assert result.models == ()


def test_undefined_application_remains_partial() -> None:
    result = solve("#nherb balance/1.\naccount(account1).\n")

    assert result.models[0].atoms == ("account(account1)",)
    assert result.models[0].assignments == ()


def test_ordinary_asp_passes_through_and_all_models_are_enumerated() -> None:
    result = solve("1 { selected(a); selected(b) } 1.\n", models=0)

    assert result.status is SolveStatus.SATISFIABLE
    assert result.exhausted
    assert {model.atoms for model in result.models} == {("selected(a)",), ("selected(b)",)}


def test_show_directive_controls_ordinary_atoms_but_not_assignments() -> None:
    result = solve(
        """#nherb balance/1.
balance(account1) #= 500.
visible.
hidden.
#show visible/0.
"""
    )

    assert result.models[0].ordinary_atoms == ("visible",)
    assert result.models[0].assignments == ("balance(account1)#=500",)
    assert "__aspf_" not in result.models[0].render()


def test_string_value_is_rendered_as_aspf_assignment() -> None:
    result = solve('#nherb label/1.\nlabel(item1) #= "cold brew".\n')

    assert result.models[0].assignments == ('label(item1)#="cold brew"',)


def test_zero_arity_assignment_is_reconstructed() -> None:
    result = solve("#nherb mode/0.\nmode #= active.\n")

    assert result.models[0].assignments == ("mode#=active",)


def test_solver_rejects_user_identifier_in_internal_namespace() -> None:
    with pytest.raises(UnsupportedSyntaxError, match="reserved for aspf-next internals"):
        solve("__aspf_injected(a).\n")


def test_solver_rejects_declared_symbol_as_ordinary_predicate() -> None:
    with pytest.raises(UnsupportedSyntaxError, match="cannot be used outside"):
        solve("#nherb balance/1.\nbalance(account1).\n")
