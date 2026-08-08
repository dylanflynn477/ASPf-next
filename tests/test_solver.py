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


def test_global_mode_reconstructs_multiple_automatic_function_symbols() -> None:
    result = solve("#nherb.\nf(a) #= 2.\nk(1) #= 2.\nsame :- f(a) #= k(1).\n")

    assert result.models[0].ordinary_atoms == ("same",)
    assert result.models[0].assignments == ("f(a)#=2", "k(1)#=2")


def test_global_mode_keeps_undefined_applications_partial() -> None:
    result = solve(
        "#nherb.\naccount(a).\nequal :- missing(a) #= 1.\ndifferent :- missing(a) #!= 1.\n"
    )

    assert result.models[0].ordinary_atoms == ("account(a)",)
    assert result.models[0].assignments == ()


def test_global_mode_supports_zero_arity_assignments_and_comparisons() -> None:
    result = solve("#nherb.\nsame :- current #= mode.\ncurrent #= active.\nmode #= active.\n")

    assert result.models[0].ordinary_atoms == ("same",)
    assert result.models[0].assignments == ("current#=active", "mode#=active")


def test_global_mode_does_not_evaluate_ordinary_herbrand_occurrences() -> None:
    result = solve("#nherb.\nf(a) #= 2.\nordinary(f(a)).\n")

    assert result.models[0].ordinary_atoms == ("ordinary(f(a))",)
    assert result.models[0].assignments == ("f(a)#=2",)


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


def test_hide_all_non_herbrand_assignments_changes_only_presentation() -> None:
    result = solve("#nherb f/1.\nf(a) #= 2.\nderived :- f(a) #= 2.\n#hide #nherb.\n")

    assert result.models[0].ordinary_atoms == ("derived",)
    assert result.models[0].assignments == ()
    assert "__aspf_value(f(a),2)." in result.lowered.source


def test_selective_hide_uses_exact_name_and_arity() -> None:
    result = solve(
        "#nherb f/0.\n#nherb f/1.\n#nherb k/1.\n"
        "f #= zero.\nf(a) #= one.\nk(a) #= other.\n"
        "#hide #nherb f/1.\n"
    )

    assert result.models[0].assignments == ("f#=zero", "k(a)#=other")


def test_selective_show_after_hide_all_exposes_only_selected_assignment() -> None:
    result = solve(
        "#nherb f/1.\n#nherb k/1.\nf(a) #= 2.\nk(a) #= 3.\n#hide #nherb.\n#show #nherb f(X).\n"
    )

    assert result.models[0].assignments == ("f(a)#=2",)


def test_visibility_directive_order_is_deterministic() -> None:
    result = solve("#nherb f/1.\nf(a) #= 2.\n#hide #nherb.\n#show #nherb f/1.\n#hide #nherb f/1.\n")

    assert result.models[0].assignments == ()


def test_ordinary_show_and_non_herbrand_visibility_are_independent() -> None:
    result = solve("#nherb f/1.\nf(a) #= 2.\nvisible.\nhidden.\n#show visible/0.\n#hide #nherb.\n")

    assert result.models[0].ordinary_atoms == ("visible",)
    assert result.models[0].assignments == ()


def test_historical_ordinary_hide_all_supports_selective_non_herbrand_show() -> None:
    result = solve(
        "#nherb f/1.\n#nherb k/1.\nf(a) #= 2.\nk(a) #= 3.\np.\n#hide.\n#show #nherb f/1.\n"
    )

    assert result.models[0].ordinary_atoms == ()
    assert result.models[0].assignments == ("f(a)#=2",)


def test_hidden_assignment_policy_is_stable_across_multiple_models() -> None:
    result = solve(
        "#nherb f/0.\n{ choose }.\nf #= 1 :- choose.\n#hide #nherb.\n",
        models=0,
    )

    assert {model.atoms for model in result.models} == {(), ("choose",)}


def test_string_value_is_rendered_as_aspf_assignment() -> None:
    result = solve('#nherb label/1.\nlabel(item1) #= "cold brew".\n')

    assert result.models[0].assignments == ('label(item1)#="cold brew"',)


def test_zero_arity_assignment_is_reconstructed() -> None:
    result = solve("#nherb mode/0.\nmode #= active.\n")

    assert result.models[0].assignments == ("mode#=active",)


def test_solver_rejects_user_identifier_in_internal_namespace() -> None:
    with pytest.raises(UnsupportedSyntaxError, match="reserved for aspf-next internals"):
        solve("__aspf_injected(a).\n")


def test_solver_preserves_declared_symbol_as_ordinary_predicate() -> None:
    result = solve("#nherb balance/1.\nbalance(account1).\n")

    assert result.models[0].ordinary_atoms == ("balance(account1)",)
    assert result.models[0].assignments == ()


def test_declared_symbol_has_separate_ordinary_and_non_herbrand_meanings() -> None:
    result = solve("#nherb k/1.\nk(1) #= 5.\nordinary(k(1)).\n")

    assert result.models[0].ordinary_atoms == ("ordinary(k(1))",)
    assert result.models[0].assignments == ("k(1)#=5",)


def test_compound_herbrand_values_preserve_identity() -> None:
    result = solve(
        "#nherb f/1.\nf(a) #= wrapper(k(1)).\n"
        "same :- f(a) #= wrapper(k(1)).\n"
        "different :- f(a) #!= wrapper(k(2)).\n"
    )

    assert result.models[0].ordinary_atoms == ("different", "same")
    assert result.models[0].assignments == ("f(a)#=wrapper(k(1))",)


def test_declared_and_undeclared_right_applications_have_different_definedness() -> None:
    undeclared = solve("#nherb f/1.\nf(a) #= k(1).\nsame :- f(a) #= k(1).\n")
    declared = solve("#nherb f/1.\n#nherb k/1.\nf(a) #= value.\nsame :- f(a) #= k(1).\n")

    assert "same" in undeclared.models[0].ordinary_atoms
    assert "same" not in declared.models[0].ordinary_atoms


def test_same_name_at_multiple_arities_keeps_values_distinct() -> None:
    result = solve(
        "#nherb f/0.\n#nherb f(X).\n#nherb f/2.\nf #= zero.\nf(a) #= one.\nf(a,b) #= two.\n"
    )

    assert result.models[0].assignments == ("f#=zero", "f(a)#=one", "f(a,b)#=two")


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


def test_historical_p1_seed_equality_is_safe_but_has_no_invented_values() -> None:
    result = solve("#nherb l/1.\np(X,Y) :- l(X) #= Y.\n")

    assert result.status is SolveStatus.SATISFIABLE
    assert result.models[0].ordinary_atoms == ()
    assert result.models[0].assignments == ()


def test_historical_p2_seed_equality_binds_key_and_value_variables() -> None:
    result = solve("#nherb l/1.\nl(a) #= 3.\np(X,Y) :- l(X) #= Y.\n")

    assert result.models[0].ordinary_atoms == ("p(a,3)",)
    assert result.models[0].assignments == ("l(a)#=3",)


def test_ground_seed_equality_binds_its_key_variable() -> None:
    result = solve("#nherb l/1.\nl(a) #= 3.\nl(b) #= 4.\np(X) :- l(X) #= 3.\n")

    assert result.models[0].ordinary_atoms == ("p(a)",)


def test_seed_equality_covers_multiple_keys_values_and_compound_values() -> None:
    result = solve(
        "#nherb l/1.\nl(a) #= 1.\nl(b) #= two.\nl(c) #= wrapper(k(3)).\np(X,Y) :- l(X) #= Y.\n"
    )

    assert result.models[0].ordinary_atoms == (
        "p(a,1)",
        "p(b,two)",
        "p(c,wrapper(k(3)))",
    )


def test_seed_equality_does_not_range_over_unrelated_constants_or_undefined_keys() -> None:
    result = solve("#nherb l/1.\nkey(a;b).\nunrelated(999).\nl(a) #= 3.\np(X,Y) :- l(X) #= Y.\n")

    assert result.models[0].ordinary_atoms == (
        "key(a)",
        "key(b)",
        "p(a,3)",
        "unrelated(999)",
    )


def test_seed_equality_follows_conditional_assignments_across_models() -> None:
    result = solve(
        "#nherb l/1.\n1 { choose(1); choose(2) } 1.\n"
        "l(a) #= 1 :- choose(1).\nl(a) #= 2 :- choose(2).\n"
        "p(X,Y) :- l(X) #= Y.\n",
        models=0,
    )

    assert {(model.ordinary_atoms, model.assignments) for model in result.models} == {
        (("choose(1)", "p(a,1)"), ("l(a)#=1",)),
        (("choose(2)", "p(a,2)"), ("l(a)#=2",)),
    }


def test_same_variable_can_join_two_seed_equalities() -> None:
    result = solve(
        "#nherb left/1.\n#nherb right/1.\n"
        "left(a) #= shared.\nright(b) #= shared.\nright(c) #= other.\n"
        "pair(X,Z,Y) :- left(X) #= Y, right(Z) #= Y.\n"
    )

    assert "pair(a,b,shared)" in result.models[0].ordinary_atoms
    assert "pair(a,c,shared)" not in result.models[0].ordinary_atoms


def test_seed_equality_can_supply_safety_to_a_dependent_literal() -> None:
    result = solve(
        "#nherb actual/1.\n#nherb expected/1.\n"
        "actual(a) #= 4.\nexpected(a) #= 4.\n"
        "same(X,Y) :- actual(X) #= Y, actual(X) #= expected(X).\n"
    )

    assert "same(a,4)" in result.models[0].ordinary_atoms


def test_independently_safe_value_variable_inequality_preserves_definedness() -> None:
    result = solve(
        "#nherb l/1.\nkey(a;b).\nvalue(1;2).\nl(a) #= 1.\n"
        "different(X,Y) :- key(X), value(Y), l(X) #!= Y.\n"
    )

    assert "different(a,2)" in result.models[0].ordinary_atoms
    assert "different(a,1)" not in result.models[0].ordinary_atoms
    assert all(not atom.startswith("different(b,") for atom in result.models[0].ordinary_atoms)


def test_default_negated_value_equality_is_nonbinding_but_works_when_independently_safe() -> None:
    result = solve(
        "#nherb l/1.\nkey(a;b).\nvalue(1;2).\nl(a) #= 1.\n"
        "missing(X,Y) :- key(X), value(Y), not l(X) #= Y.\n"
    )

    assert "missing(a,1)" not in result.models[0].ordinary_atoms
    assert "missing(a,2)" in result.models[0].ordinary_atoms
    assert "missing(b,1)" in result.models[0].ordinary_atoms
    assert "missing(b,2)" in result.models[0].ordinary_atoms


def application_comparison_program(
    operator: str,
    left_value: str | None,
    right_value: str | None,
) -> str:
    assignments = ""
    if left_value is not None:
        assignments += f"actual #= {left_value}.\n"
    if right_value is not None:
        assignments += f"expected #= {right_value}.\n"
    return (
        f"#nherb actual/0.\n#nherb expected/0.\n{assignments}holds :- actual {operator} expected.\n"
    )


@pytest.mark.parametrize(
    ("left_value", "right_value", "expected"),
    [
        ("10", "10", True),
        ("10", "20", False),
        (None, "10", False),
        ("10", None, False),
        (None, None, False),
        ("active", "active", True),
        ('"same"', '"same"', True),
    ],
)
def test_application_equality_requires_two_defined_equal_values(
    left_value: str | None, right_value: str | None, expected: bool
) -> None:
    result = solve(application_comparison_program("#=", left_value, right_value))

    assert ("holds" in result.models[0].ordinary_atoms) is expected


@pytest.mark.parametrize(
    ("left_value", "right_value", "expected"),
    [
        ("10", "20", True),
        ("10", "10", False),
        (None, "10", False),
        ("10", None, False),
        (None, None, False),
        ("active", "idle", True),
        ('"left"', '"right"', True),
    ],
)
def test_application_inequality_requires_two_defined_different_values(
    left_value: str | None, right_value: str | None, expected: bool
) -> None:
    result = solve(application_comparison_program("#!=", left_value, right_value))

    assert ("holds" in result.models[0].ordinary_atoms) is expected


@pytest.mark.parametrize(
    ("operator", "left_value", "right_value", "expected"),
    [
        ("#<", "-2", "0", True),
        ("#<=", "0", "0", True),
        ("#>", "2", "-1", True),
        ("#>=", "0", "0", True),
        ("#<", "1", "0", False),
        ("#<=", "1", "0", False),
        ("#>", "-1", "0", False),
        ("#>=", "-1", "0", False),
        ("#<", None, "0", False),
        ("#<", "0", None, False),
        ("#<", "symbolic", "1", False),
        ("#<", "1", "symbolic", False),
        ("#<", '"0"', "1", False),
        ("#<", "1", '"2"', False),
        ("#<", "-10", "5", True),
    ],
)
def test_ordered_application_comparison_requires_two_defined_integers(
    operator: str,
    left_value: str | None,
    right_value: str | None,
    expected: bool,
) -> None:
    result = solve(application_comparison_program(operator, left_value, right_value))

    assert ("holds" in result.models[0].ordinary_atoms) is expected


def test_application_comparison_supports_same_domain_variable_on_both_sides() -> None:
    result = solve(
        """#nherb actual/1.
#nherb expected/1.
account(a;b;c).
actual(a) #= 10.
expected(a) #= 10.
actual(b) #= 20.
expected(b) #= 25.
same(A) :- account(A), actual(A) #= expected(A).
different(A) :- account(A), actual(A) #!= expected(A).
"""
    )

    assert "same(a)" in result.models[0].ordinary_atoms
    assert "different(b)" in result.models[0].ordinary_atoms
    assert "same(c)" not in result.models[0].ordinary_atoms
    assert "different(c)" not in result.models[0].ordinary_atoms


def test_application_comparison_supports_two_independently_safe_variables() -> None:
    result = solve(
        """#nherb actual/1.
#nherb expected/1.
account(a;b).
actual(a) #= match.
expected(b) #= match.
pair(A,B) :- account(A), account(B), actual(A) #= expected(B).
"""
    )

    assert "pair(a,b)" in result.models[0].ordinary_atoms


def test_assignment_head_and_application_comparison_coexist_without_copying() -> None:
    result = solve(
        """#nherb actual/1.
#nherb expected/1.
account(a).
expected(a) #= 10.
actual(A) #= 10 :- account(A).
same(A) :- account(A), actual(A) #= expected(A).
"""
    )

    assert "same(a)" in result.models[0].ordinary_atoms
    assert result.models[0].assignments == ("actual(a)#=10", "expected(a)#=10")


def test_application_comparisons_follow_ordinary_choices_across_models() -> None:
    result = solve(
        """#nherb actual/0.
#nherb expected/0.
1 { choose(equal); choose(different) } 1.
expected #= 10.
actual #= 10 :- choose(equal).
actual #= 20 :- choose(different).
same :- actual #= expected.
changed :- actual #!= expected.
""",
        models=0,
    )

    assert {model.ordinary_atoms for model in result.models} == {
        ("changed", "choose(different)"),
        ("choose(equal)", "same"),
    }


@pytest.mark.parametrize(
    ("assigned", "expected"),
    [("5", False), ("6", True), (None, True)],
)
def test_default_negated_scalar_equality_is_failure_of_positive_satisfaction(
    assigned: str | None, expected: bool
) -> None:
    assignment = f"f #= {assigned}.\n" if assigned is not None else ""
    result = solve(f"#nherb f/0.\n{assignment}p :- not f #= 5.\n")

    assert ("p" in result.models[0].ordinary_atoms) is expected


@pytest.mark.parametrize(
    ("assigned", "expected"),
    [("6", False), ("5", True), (None, True)],
)
def test_default_negated_scalar_inequality_is_failure_of_positive_satisfaction(
    assigned: str | None, expected: bool
) -> None:
    assignment = f"f #= {assigned}.\n" if assigned is not None else ""
    result = solve(f"#nherb f/0.\n{assignment}p :- not f #!= 5.\n")

    assert ("p" in result.models[0].ordinary_atoms) is expected


def test_undefined_default_negated_inequality_is_not_positive_equality() -> None:
    result = solve("#nherb f/0.\nnegated_neq :- not f #!= 5.\npositive_eq :- f #= 5.\n")

    assert result.models[0].ordinary_atoms == ("negated_neq",)


@pytest.mark.parametrize(
    ("operator", "assigned", "right", "expected"),
    [
        ("#<", "-1", "0", False),
        ("#<", "1", "0", True),
        ("#<", None, "0", True),
        ("#<", "active", "0", True),
        ("#<", '"-1"', "0", True),
        ("#<", "-2", "-1", False),
        ("#<", "0", "1", False),
        ("#<", "1", "1", True),
        ("#<=", "0", "0", False),
        ("#<=", "1", "0", True),
        ("#<=", None, "0", True),
        ("#<=", "active", "0", True),
        ("#<=", '"0"', "0", True),
        ("#<=", "-1", "-1", False),
        ("#<=", "0", "0", False),
        ("#<=", "1", "0", True),
        ("#>", "1", "0", False),
        ("#>", "-1", "0", True),
        ("#>", None, "0", True),
        ("#>", "active", "0", True),
        ("#>", '"1"', "0", True),
        ("#>", "-1", "-2", False),
        ("#>", "0", "-1", False),
        ("#>", "1", "1", True),
        ("#>=", "0", "0", False),
        ("#>=", "-1", "0", True),
        ("#>=", None, "0", True),
        ("#>=", "active", "0", True),
        ("#>=", '"0"', "0", True),
        ("#>=", "-1", "-1", False),
        ("#>=", "0", "0", False),
        ("#>=", "-1", "0", True),
    ],
)
def test_default_negated_ordered_scalar_truth_table(
    operator: str, assigned: str | None, right: str, expected: bool
) -> None:
    assignment = f"value #= {assigned}.\n" if assigned is not None else ""
    result = solve(f"#nherb value/0.\n{assignment}holds :- not value {operator} {right}.\n")

    assert ("holds" in result.models[0].ordinary_atoms) is expected


@pytest.mark.parametrize(
    ("operator", "left", "right", "expected"),
    [
        ("#=", "10", "10", False),
        ("#=", "10", "20", True),
        ("#=", None, "10", True),
        ("#=", "10", None, True),
        ("#=", None, None, True),
        ("#!=", "10", "20", False),
        ("#!=", "10", "10", True),
        ("#!=", None, "10", True),
        ("#!=", "10", None, True),
        ("#!=", None, None, True),
    ],
)
def test_default_negated_application_equality_and_inequality_truth_tables(
    operator: str, left: str | None, right: str | None, expected: bool
) -> None:
    assignments = ""
    if left is not None:
        assignments += f"actual #= {left}.\n"
    if right is not None:
        assignments += f"expected #= {right}.\n"
    result = solve(
        f"#nherb actual/0.\n#nherb expected/0.\n{assignments}"
        f"holds :- not actual {operator} expected.\n"
    )

    assert ("holds" in result.models[0].ordinary_atoms) is expected


@pytest.mark.parametrize(
    ("operator", "left", "right", "expected"),
    [
        ("#<", "1", "2", False),
        ("#<=", "2", "1", True),
        ("#>", None, "1", True),
        ("#>=", "1", None, True),
        ("#<", None, None, True),
        ("#<", "active", "1", True),
        ("#<", "1", "active", True),
        ("#<", '"1"', '"2"', True),
    ],
)
def test_default_negated_ordered_application_truth_table(
    operator: str, left: str | None, right: str | None, expected: bool
) -> None:
    assignments = ""
    if left is not None:
        assignments += f"actual #= {left}.\n"
    if right is not None:
        assignments += f"expected #= {right}.\n"
    result = solve(
        f"#nherb actual/0.\n#nherb expected/0.\n{assignments}"
        f"holds :- not actual {operator} expected.\n"
    )

    assert ("holds" in result.models[0].ordinary_atoms) is expected


def test_default_negated_variable_comparison_keeps_undefined_ground_instance() -> None:
    result = solve(
        """#nherb balance/1.
account(a;b;c).
balance(a) #= 500.
balance(b) #= 1500.
not_high(A) :- account(A), not balance(A) #>= 1000.
"""
    )

    assert result.models[0].ordinary_atoms == (
        "account(a)",
        "account(b)",
        "account(c)",
        "not_high(a)",
        "not_high(c)",
    )


def test_default_negated_helper_identity_keeps_multi_variable_groundings_distinct() -> None:
    result = solve(
        """#nherb actual/1.
#nherb expected/1.
account(a;b).
actual(a) #= same.
expected(a) #= same.
expected(b) #= other.
pair(A,B) :- account(A), account(B), not actual(A) #= expected(B).
"""
    )

    assert {atom for atom in result.models[0].ordinary_atoms if atom.startswith("pair(")} == {
        "pair(a,b)",
        "pair(b,a)",
        "pair(b,b)",
    }


def test_multiple_default_negated_comparisons_are_independent_per_grounding() -> None:
    result = solve(
        """#nherb balance/1.
#nherb score/1.
account(a;b;c).
balance(a) #= 500.
score(a) #= 75.
balance(b) #= 1500.
score(b) #= 75.
review(A) :- account(A), not balance(A) #>= 1000, not score(A) #< 50.
"""
    )

    assert "review(a)" in result.models[0].ordinary_atoms
    assert "review(b)" not in result.models[0].ordinary_atoms
    assert "review(c)" in result.models[0].ordinary_atoms


def test_historical_default_assignment_idiom_preserves_reduct_behavior() -> None:
    result = solve(
        "#nherb value/0.\nchoose_default :- not value #!= 1.\nvalue #= 1 :- choose_default.\n"
    )

    assert result.status is SolveStatus.SATISFIABLE
    assert result.models[0].ordinary_atoms == ("choose_default",)
    assert result.models[0].assignments == ("value#=1",)


def test_recursive_default_negated_equality_odd_loop_has_no_stable_model() -> None:
    result = solve("#nherb value/0.\ntrigger :- not value #= 1.\nvalue #= 1 :- trigger.\n")

    assert result.status is SolveStatus.UNSATISFIABLE
    assert result.models == ()


def test_default_negated_n_atom_follows_each_ordinary_choice_model() -> None:
    result = solve(
        """#nherb value/0.
{ choose }.
value #= 1 :- choose.
missing :- not value #= 1.
""",
        models=0,
    )

    assert {model.atoms for model in result.models} == {
        ("missing",),
        ("choose", "value#=1"),
    }
    assert all(not atom.startswith("__aspf_") for model in result.models for atom in model.atoms)
