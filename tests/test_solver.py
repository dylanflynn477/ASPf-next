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


def test_defined_different_value_satisfies_not_equal() -> None:
    result = solve(
        "#nherb balance/1.\nbalance(account1) #= 600.\ndifferent :- balance(account1) #!= 500.\n"
    )

    assert result.models[0].ordinary_atoms == ("different",)
    assert result.models[0].assignments == ("balance(account1)#=600",)


def test_defined_equal_value_does_not_satisfy_not_equal() -> None:
    result = solve(
        "#nherb balance/1.\nbalance(account1) #= 500.\ndifferent :- balance(account1) #!= 500.\n"
    )

    assert result.models[0].ordinary_atoms == ()
    assert result.models[0].assignments == ("balance(account1)#=500",)


def test_undefined_application_does_not_satisfy_not_equal() -> None:
    result = solve(
        "#nherb balance/1.\naccount(account1).\ndifferent :- balance(account1) #!= 500.\n"
    )

    assert result.models[0].ordinary_atoms == ("account(account1)",)
    assert result.models[0].assignments == ()


@pytest.mark.parametrize(
    ("source", "expected_assignment"),
    [
        (
            '#nherb label/1.\nlabel(item) #= "cold".\ndifferent :- label(item) #!= "hot".\n',
            'label(item)#="cold"',
        ),
        (
            "#nherb temperature/1.\ntemperature(room) #= -3.\n"
            "different :- temperature(room) #!= -2.\n",
            "temperature(room)#=-3",
        ),
        (
            "#nherb mode/0.\nmode #= active.\ndifferent :- mode #!= idle.\n",
            "mode#=active",
        ),
    ],
)
def test_not_equal_supports_strings_negative_integers_and_zero_arity(
    source: str, expected_assignment: str
) -> None:
    result = solve(source)

    assert result.models[0].ordinary_atoms == ("different",)
    assert result.models[0].assignments == (expected_assignment,)


def test_equality_and_not_equal_cannot_both_hold_for_the_same_value() -> None:
    result = solve(
        "#nherb balance/1.\nbalance(account1) #= 500.\n"
        "equal :- balance(account1) #= 500.\n"
        "not_equal :- balance(account1) #!= 500.\n"
    )

    assert result.models[0].ordinary_atoms == ("equal",)


def test_not_equal_tracks_assignments_across_multiple_models() -> None:
    result = solve(
        """#nherb level/1.
1 { choose(one); choose(two) } 1.
level(item) #= 1 :- choose(one).
level(item) #= 2 :- choose(two).
different :- level(item) #!= 1.
""",
        models=0,
    )

    assert {model.atoms for model in result.models} == {
        ("choose(one)", "level(item)#=1"),
        ("choose(two)", "different", "level(item)#=2"),
    }


@pytest.mark.parametrize(
    ("operator", "assigned", "right"),
    [
        ("#<", -1, 0),
        ("#<=", 0, 0),
        ("#>", 1, 0),
        ("#>=", 0, 0),
    ],
)
def test_each_ordered_operator_succeeds_when_true(operator: str, assigned: int, right: int) -> None:
    result = solve(f"#nherb value/0.\nvalue #= {assigned}.\nokay :- value {operator} {right}.\n")

    assert result.models[0].ordinary_atoms == ("okay",)


@pytest.mark.parametrize(
    ("operator", "assigned", "right"),
    [
        ("#<", 0, 0),
        ("#<=", 1, 0),
        ("#>", 0, 0),
        ("#>=", -1, 0),
    ],
)
def test_each_ordered_operator_fails_when_false(operator: str, assigned: int, right: int) -> None:
    result = solve(f"#nherb value/0.\nvalue #= {assigned}.\nokay :- value {operator} {right}.\n")

    assert result.models[0].ordinary_atoms == ()


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
def test_each_ordered_operator_fails_for_undefined_application(operator: str) -> None:
    result = solve(f"#nherb value/0.\nokay :- value {operator} 0.\n")

    assert result.models[0].ordinary_atoms == ()
    assert result.models[0].assignments == ()


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
@pytest.mark.parametrize("assigned", ["symbolic", '"5"'])
def test_ordered_comparison_fails_for_defined_noninteger_value(
    operator: str, assigned: str
) -> None:
    result = solve(f"#nherb value/0.\nvalue #= {assigned}.\nokay :- value {operator} 0.\n")

    assert result.models[0].ordinary_atoms == ()


@pytest.mark.parametrize(
    ("operator", "right"),
    [("#<", 2), ("#<=", 1), ("#>", -2), ("#>=", -1)],
)
@pytest.mark.parametrize("assigned", [-1, 0, 1])
def test_each_ordered_operator_accepts_negative_zero_and_positive_integer_values(
    operator: str, right: int, assigned: int
) -> None:
    result = solve(f"#nherb value/0.\nvalue #= {assigned}.\nokay :- value {operator} {right}.\n")

    assert result.models[0].ordinary_atoms == ("okay",)


def test_ordered_comparison_interacts_with_equal_and_not_equal() -> None:
    result = solve(
        "#nherb value/0.\nvalue #= 5.\n"
        "equal :- value #= 5.\n"
        "different :- value #!= 4.\n"
        "ordered :- value #> 0.\n"
    )

    assert result.models[0].ordinary_atoms == ("different", "equal", "ordered")


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
    with pytest.raises(UnsupportedSyntaxError, match="may only be used as the key"):
        solve("#nherb balance/1.\nbalance(account1).\n")


def test_domain_safe_variable_comparisons_preserve_definedness() -> None:
    result = solve(
        """#nherb balance/1.
account(a;b;c).
balance(a) #= 500.
balance(b) #= 1500.
equal(A) :- account(A), balance(A) #= 500.
different(A) :- account(A), balance(A) #!= 500.
low(A) :- account(A), balance(A) #< 1000.
"""
    )

    assert result.models[0].ordinary_atoms == (
        "account(a)",
        "account(b)",
        "account(c)",
        "different(b)",
        "equal(a)",
        "low(a)",
    )
    assert result.models[0].assignments == ("balance(a)#=500", "balance(b)#=1500")


@pytest.mark.parametrize(
    ("operator", "assigned", "right"),
    [("#<", -1, 0), ("#<=", 0, 0), ("#>", 1, 0), ("#>=", 0, 0)],
)
def test_domain_safe_variable_supports_every_ordered_operator(
    operator: str, assigned: int, right: int
) -> None:
    result = solve(
        "#nherb value/1.\nitem(a;b).\n"
        f"value(a) #= {assigned}.\nok(X) :- item(X), value(X) {operator} {right}.\n"
    )

    assert "ok(a)" in result.models[0].ordinary_atoms
    assert "ok(b)" not in result.models[0].ordinary_atoms


def test_domain_safe_variable_assignment_head_grounds_over_ordinary_domain() -> None:
    result = solve("#nherb status/1.\nperson(alice;bob).\nstatus(P) #= active :- person(P).\n")

    assert result.models[0].assignments == (
        "status(alice)#=active",
        "status(bob)#=active",
    )


def test_domain_safe_variable_head_assignments_retain_functionality() -> None:
    result = solve(
        "#nherb status/1.\nperson(alice).\n"
        "status(P) #= active :- person(P).\n"
        "status(P) #= inactive :- person(P).\n"
    )

    assert result.status is SolveStatus.UNSATISFIABLE
    assert result.models == ()
