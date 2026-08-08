from __future__ import annotations

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program
from aspf_next.lowering import (
    FUNCTIONALITY_CONSTRAINT,
    INTERNAL_DEFINITIONS,
    INTERNAL_INTEGER_PREDICATE,
    TemporaryAllocator,
    lower_program,
)


def lowered(source: str) -> str:
    return lower_program(parse_program(source)).source


def test_lowers_basic_assignment_and_functionality() -> None:
    result = lowered("#nherb balance/1.\nbalance(account1) #= 500.\n")

    assert "__aspf_value(balance(account1),500)." in result
    assert result.count(FUNCTIONALITY_CONSTRAINT) == 1


def test_lowers_global_assignment_and_functionality_without_explicit_declarations() -> None:
    result = lowered("#nherb.\nbalance(account1) #= 500.\n")

    assert "__aspf_value(balance(account1),500)." in result
    assert result.count(FUNCTIONALITY_CONSTRAINT) == 1


def test_lowers_global_application_comparison_as_two_defined_lookups() -> None:
    result = lowered("#nherb.\nf(a) #= 2.\nk(1) #= 2.\nsame :- f(a) #= k(1).\n")

    assert "same :- __aspf_value(f(a),_AspfCmp0), __aspf_value(k(1),_AspfCmp0)." in result


def test_lowers_global_zero_arity_application_comparison() -> None:
    result = lowered("#nherb.\nsame :- current #= mode.\ncurrent #= active.\nmode #= active.\n")

    assert "same :- __aspf_value(current,_AspfCmp0), __aspf_value(mode,_AspfCmp0)." in result


def test_non_herbrand_visibility_directives_do_not_enter_solver_program() -> None:
    result = lowered("#nherb f/1.\nf(a) #= 2.\n#hide #nherb.\n#show #nherb f/1.\n")

    assert "__aspf_value(f(a),2)." in result
    assert "#hide #nherb" not in result
    assert "#show #nherb" not in result


def test_historical_ordinary_hide_all_lowers_to_modern_show_empty() -> None:
    result = lowered("p.\n#hide.\n#show p/0.\n")

    assert "#hide." not in result
    assert "#show." in result
    assert "#show p/0." in result


def test_lowers_positive_body_comparison() -> None:
    result = lowered(
        """#nherb balance/1.
balance(account1) #= 500.
solvent(account1) :- balance(account1) #= 500.
"""
    )

    assert "solvent(account1) :- __aspf_value(balance(account1),500)." in result


def test_lowers_not_equal_to_a_defined_value_lookup_and_comparison() -> None:
    result = lowered("#nherb balance/1.\ndifferent :- balance(account1) #!= 500.\n")

    assert "different :- __aspf_value(balance(account1),_AspfNeq0), _AspfNeq0 != 500." in result
    assert "not __aspf_value" not in result


def test_not_equal_lowering_uses_collision_free_rule_local_variables() -> None:
    result = lowered(
        "#nherb balance/1.\ndifferent(_AspfNeq0) :- item(_AspfNeq0), balance(account1) #!= 500.\n"
    )

    assert "__aspf_value(balance(account1),_AspfNeq1)" in result
    assert "_AspfNeq1 != 500" in result


def test_lowers_multiple_not_equal_comparisons_with_distinct_variables() -> None:
    result = lowered(
        "#nherb left/1.\n#nherb right/1.\ndifferent :- left(a) #!= 1, right(b) #!= 2.\n"
    )

    assert "__aspf_value(left(a),_AspfNeq0), _AspfNeq0 != 1" in result
    assert "__aspf_value(right(b),_AspfNeq1), _AspfNeq1 != 2" in result


def test_equality_and_not_equal_share_the_value_relation() -> None:
    result = lowered(
        "#nherb balance/1.\nbalance(account1) #= 500.\n"
        "same :- balance(account1) #= 500.\n"
        "different :- balance(account1) #!= 600.\n"
    )

    assert "same :- __aspf_value(balance(account1),500)." in result
    assert "__aspf_value(balance(account1),_AspfNeq0), _AspfNeq0 != 600" in result


@pytest.mark.parametrize(
    ("operator", "clingo_operator"),
    [("#<", "<"), ("#<=", "<="), ("#>", ">"), ("#>=", ">=")],
)
def test_lowers_each_ordered_operator_through_shared_integer_lookup(
    operator: str, clingo_operator: str
) -> None:
    result = lowered(
        f"#nherb balance/1.\nbalance(account1) #= -5.\nokay :- balance(account1) {operator} 0.\n"
    )

    assert f"{INTERNAL_INTEGER_PREDICATE}(-5)." in result
    assert (
        "okay :- __aspf_value(balance(account1),_AspfCmp0), "
        f"__aspf_integer(_AspfCmp0), _AspfCmp0 {clingo_operator} 0."
    ) in result


def test_ordered_lowering_tags_only_integer_assignment_values() -> None:
    result = lowered(
        '#nherb value/1.\nvalue(number) #= 7.\nvalue(symbol) #= seven.\nvalue(string) #= "7".\n'
    )

    assert "__aspf_integer(7)." in result
    assert "__aspf_integer(seven)." not in result
    assert '__aspf_integer("7").' not in result


def test_ordered_lowering_uses_collision_free_shared_comparison_path() -> None:
    result = lowered(
        "#nherb balance/1.\n"
        "okay(_AspfCmp0) :- item(_AspfCmp0), balance(account1) #>= 0, "
        "balance(account1) #!= 10.\n"
    )

    assert "__aspf_value(balance(account1),_AspfCmp1)" in result
    assert "_AspfCmp1 >= 0" in result
    assert "__aspf_value(balance(account1),_AspfNeq2)" in result
    assert "_AspfNeq2 != 10" in result


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
    assert INTERNAL_DEFINITIONS in result
    assert FUNCTIONALITY_CONSTRAINT in result


def test_lowering_rejects_user_identifier_in_internal_namespace() -> None:
    with pytest.raises(UnsupportedSyntaxError, match="reserved for aspf-next internals"):
        lowered("__aspf_value(user,key).\n")


def test_lowering_preserves_declared_symbol_as_ordinary_term() -> None:
    result = lowered("#nherb balance/1.\np(balance(account1)).\n")

    assert "p(balance(account1))." in result
    assert INTERNAL_DEFINITIONS in result


def test_lowers_compound_herbrand_assignment_and_comparison_values() -> None:
    result = lowered(
        "#nherb status/1.\nstatus(alice) #= wrapper(k(1)).\n"
        "same :- status(alice) #= wrapper(k(1)).\n"
        "different :- status(alice) #!= wrapper(k(2)).\n"
    )

    assert "__aspf_value(status(alice),wrapper(k(1)))." in result
    assert "same :- __aspf_value(status(alice),wrapper(k(1)))." in result
    assert "_AspfNeq0 != wrapper(k(2))" in result


def test_lowers_domain_safe_variable_assignment_head_without_emitting_a_domain_rule() -> None:
    result = lowered("#nherb status/1.\nperson(alice;bob).\nstatus(P) #= active :- person(P).\n")

    assert "__aspf_value(status(P),active) :- person(P)." in result
    assert "person(P) :-" not in result


def test_lowers_domain_safe_variable_positive_equality() -> None:
    result = lowered("#nherb balance/1.\nzero(A) :- account(A), balance(A) #= 0.\n")

    assert "zero(A) :- account(A), __aspf_value(balance(A),0)." in result


def test_lowers_domain_safe_variable_not_equal_with_definedness_lookup() -> None:
    result = lowered("#nherb balance/1.\nnonzero(A) :- account(A), balance(A) #!= 0.\n")

    assert (
        "nonzero(A) :- account(A), __aspf_value(balance(A),_AspfNeq0), _AspfNeq0 != 0."
    ) in result


def test_lowers_domain_safe_variable_ordered_comparison_with_integer_guard() -> None:
    result = lowered("#nherb balance/1.\nlow(A) :- account(A), balance(A) #< 1000.\n")

    assert (
        "low(A) :- account(A), __aspf_value(balance(A),_AspfCmp0), "
        "__aspf_integer(_AspfCmp0), _AspfCmp0 < 1000."
    ) in result


def test_variable_lowering_keeps_generated_comparison_helpers_collision_free() -> None:
    result = lowered(
        "#nherb balance/1.\n"
        "low(A,_AspfCmp0) :- account(A), marker(_AspfCmp0), balance(A) #< 1000.\n"
    )

    assert "__aspf_value(balance(A),_AspfCmp1)" in result
    assert "_AspfCmp1 < 1000" in result


def test_temporary_allocator_is_deterministic_and_skips_all_used_names() -> None:
    allocator = TemporaryAllocator({"_AspfCmp0", "_AspfCmp2", "ordinary"})

    assert allocator.new("_AspfCmp") == "_AspfCmp1"
    assert allocator.new("_AspfCmp") == "_AspfCmp3"
    assert allocator.new("_AspfNeq") == "_AspfNeq4"


def test_temporary_allocator_copies_its_input_set() -> None:
    identifiers = {"_AspfCmp0"}
    allocator = TemporaryAllocator(identifiers)

    assert allocator.new("_AspfCmp") == "_AspfCmp1"
    assert identifiers == {"_AspfCmp0"}


def test_lowers_application_equality_with_one_shared_defined_value() -> None:
    result = lowered(
        "#nherb actual/1.\n#nherb expected/1.\nsame(A) :- account(A), actual(A) #= expected(A).\n"
    )

    assert (
        "same(A) :- account(A), __aspf_value(actual(A),_AspfCmp0), "
        "__aspf_value(expected(A),_AspfCmp0)."
    ) in result


def test_lowers_application_inequality_with_two_defined_values() -> None:
    result = lowered(
        "#nherb actual/1.\n#nherb expected/1.\n"
        "different(A) :- account(A), actual(A) #!= expected(A).\n"
    )

    assert (
        "different(A) :- account(A), __aspf_value(actual(A),_AspfCmp0), "
        "__aspf_value(expected(A),_AspfCmp1), _AspfCmp0 != _AspfCmp1."
    ) in result


@pytest.mark.parametrize(
    ("operator", "clingo_operator"), [("#<", "<"), ("#<=", "<="), ("#>", ">"), ("#>=", ">=")]
)
def test_lowers_ordered_application_comparison_with_two_integer_guards(
    operator: str, clingo_operator: str
) -> None:
    result = lowered(f"#nherb actual/0.\n#nherb expected/0.\nokay :- actual {operator} expected.\n")

    assert "__aspf_value(actual,_AspfCmp0)" in result
    assert "__aspf_value(expected,_AspfCmp1)" in result
    assert "__aspf_integer(_AspfCmp0)" in result
    assert "__aspf_integer(_AspfCmp1)" in result
    assert f"_AspfCmp0 {clingo_operator} _AspfCmp1" in result


def test_application_comparison_temporaries_avoid_multiple_source_collisions() -> None:
    result = lowered(
        "#nherb actual/1.\n#nherb expected/1.\n"
        "different(A,_AspfCmp0,_AspfCmp1) :- account(A), marker(_AspfCmp0), "
        "marker(_AspfCmp1), actual(A) #!= expected(A).\n"
    )

    assert "__aspf_value(actual(A),_AspfCmp2)" in result
    assert "__aspf_value(expected(A),_AspfCmp3)" in result
    assert "_AspfCmp2 != _AspfCmp3" in result


@pytest.mark.parametrize(
    ("operator", "positive_body"),
    [
        ("#=", "__aspf_value(balance(A),1000)"),
        ("#!=", "__aspf_value(balance(A),_AspfNeq0), _AspfNeq0 != 1000"),
        (
            "#>=",
            "__aspf_value(balance(A),_AspfCmp0), __aspf_integer(_AspfCmp0), _AspfCmp0 >= 1000",
        ),
    ],
)
def test_default_negation_names_positive_satisfaction_before_negating_it(
    operator: str, positive_body: str
) -> None:
    result = lowered(f"#nherb balance/1.\nflag(A) :- account(A), not balance(A) {operator} 1000.\n")

    assert "flag(A) :- account(A), not __aspf_sat_0(A)." in result
    assert f"__aspf_sat_0(A) :- {positive_body}." in result


def test_default_negated_application_comparison_helper_has_stable_variable_identity() -> None:
    result = lowered(
        "#nherb actual/1.\n#nherb expected/1.\n"
        "pair(A,B) :- account(A), account(B), not actual(A) #= expected(B).\n"
    )

    assert "pair(A,B) :- account(A), account(B), not __aspf_sat_0(A,B)." in result
    assert (
        "__aspf_sat_0(A,B) :- __aspf_value(actual(A),_AspfCmp0), "
        "__aspf_value(expected(B),_AspfCmp0)."
    ) in result


def test_multiple_default_negated_comparisons_get_independent_helpers() -> None:
    result = lowered(
        "#nherb balance/1.\n#nherb score/1.\n"
        "review(A) :- account(A), not balance(A) #>= 1000, not score(A) #< 50.\n"
    )

    assert "not __aspf_sat_0(A), not __aspf_sat_1(A)" in result
    assert result.count("__aspf_sat_0(A) :-") == 1
    assert result.count("__aspf_sat_1(A) :-") == 1


def test_helper_allocation_is_program_local_and_deterministic() -> None:
    source = "#nherb value/0.\nflag :- not value #= 1.\n"

    first = lowered(source)
    second = lowered(source)

    assert first == second
    assert "flag :- not __aspf_sat_0." in first
    assert "__aspf_sat_1" not in first


def test_positive_comparison_lowering_does_not_gain_satisfaction_helpers() -> None:
    result = lowered("#nherb value/0.\nflag :- value #!= 1.\n")

    assert "flag :- __aspf_value(value,_AspfNeq0), _AspfNeq0 != 1." in result
    assert "__aspf_sat_" not in result
