from __future__ import annotations

from typing import cast

import pytest

from research.native_backend import (
    AppExpression,
    Application,
    AssignmentHead,
    Atom,
    AtomHead,
    Choice,
    Comparison,
    ComparisonOperator,
    ConstantExpression,
    Definition,
    Integer,
    NativeProgram,
    NativeRule,
    NativeSolver,
    NativeValidationError,
    NVariable,
    NVariableExpression,
    Seed,
    SourceLocation,
    String,
    Symbol,
    Variable,
)
from research.native_backend.differential import compare_with_reference
from research.native_backend.ir import Term

X = Symbol("x")


def _app(function: str, argument: Symbol | Variable = X) -> Application:
    return Application(function, (argument,))


def _copy_rule(
    *,
    identifier: str = "copy",
    source: Application | None = None,
    target: Application | None = None,
    when: tuple[Atom, ...] = (),
) -> NativeRule:
    variable = NVariable("_v")
    return NativeRule(
        identifier,
        AssignmentHead(target or _app("h"), NVariableExpression(variable)),
        definitions=(Definition(variable, AppExpression(source or _app("f"))),),
        when=when,
    )


def test_smallest_copy_keeps_nvariable_out_of_ordinary_grounding() -> None:
    program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(5)),),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program)

    assert [model.visible for model in result.models] == [("f(x)#=5", "h(x)#=5")]
    assert "_v" not in result.internal_source
    assert "nvar(v)" in result.internal_source
    assert "ordinary(v)" not in result.internal_source
    assert result.theory_atoms == 2


@pytest.mark.parametrize(
    ("value", "rendered"),
    [
        (Integer(-2), "-2"),
        (Symbol("active"), "active"),
        (String('a "quote"'), '"a \\"quote\\""'),
    ],
)
def test_copy_preserves_typed_values(value: Integer | Symbol | String, rendered: str) -> None:
    result = NativeSolver().solve(
        NativeProgram(seeds=(Seed(_app("f"), value),), rules=(_copy_rule(),))
    )

    assert result.models[0].assignments == (f"f(x)#={rendered}", f"h(x)#={rendered}")


def test_backtracking_models_do_not_leak_values_between_branches() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 2),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program)

    assert [model.visible for model in result.models] == [
        ("choose(1)", "f(x)#=1", "h(x)#=1"),
        ("choose(2)", "f(x)#=2", "h(x)#=2"),
    ]
    assert result.undo_count >= 1


def test_functionality_rejects_conflicting_application_values() -> None:
    program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(1)), Seed(_app("f"), Integer(2))),
    )
    reference = """
    __bench_value(f(x),1).
    __bench_value(f(x),2).
    :- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.
    """

    comparison = compare_with_reference(program, reference)

    assert comparison.equivalent
    assert comparison.native == ()


def test_partial_source_leaves_nvariable_and_target_undefined() -> None:
    result = NativeSolver().solve(NativeProgram(rules=(_copy_rule(),)))

    assert result.models[0].assignments == ()
    assert result.models[0].undefined_nvariables == ("copy:_v",)


def test_defined_zero_is_not_confused_with_undefined() -> None:
    result = NativeSolver().solve(
        NativeProgram(
            seeds=(Seed(_app("f"), Integer(0)),),
            rules=(
                NativeRule(
                    "zero",
                    AtomHead(Atom("is_zero")),
                    comparisons=(
                        Comparison(
                            AppExpression(_app("f")),
                            ComparisonOperator.EQUAL,
                            ConstantExpression(Integer(0)),
                        ),
                    ),
                ),
            ),
        )
    )

    assert result.models[0].visible == ("f(x)#=0", "is_zero")


def test_multiple_agreeing_definitions_bind_one_value() -> None:
    variable = NVariable("_v")
    rule = NativeRule(
        "agree",
        AssignmentHead(_app("h"), NVariableExpression(variable)),
        definitions=(
            Definition(variable, AppExpression(_app("f"))),
            Definition(variable, AppExpression(_app("g"))),
        ),
    )
    result = NativeSolver().solve(
        NativeProgram(
            seeds=(Seed(_app("f"), Integer(5)), Seed(_app("g"), Integer(5))),
            rules=(rule,),
        )
    )

    assert result.models[0].assignments == ("f(x)#=5", "g(x)#=5", "h(x)#=5")


@pytest.mark.parametrize("second_value", [Integer(6), None])
def test_conflicting_or_undefined_definition_makes_nvariable_undefined(
    second_value: Integer | None,
) -> None:
    variable = NVariable("_v")
    seeds = [Seed(_app("f"), Integer(5))]
    if second_value is not None:
        seeds.append(Seed(_app("g"), second_value))
    rule = NativeRule(
        "undefined_definition",
        AssignmentHead(_app("h"), NVariableExpression(variable)),
        definitions=(
            Definition(variable, AppExpression(_app("f"))),
            Definition(variable, AppExpression(_app("g"))),
        ),
    )

    result = NativeSolver().solve(NativeProgram(seeds=tuple(seeds), rules=(rule,)))

    assert all(not assignment.startswith("h(") for assignment in result.models[0].assignments)
    assert result.models[0].undefined_nvariables == ("undefined_definition:_v",)


def test_multiple_level_nvariable_definitions_are_evaluated_in_order() -> None:
    first = NVariable("_first")
    second = NVariable("_second")
    rule = NativeRule(
        "levels",
        AssignmentHead(_app("h"), NVariableExpression(second)),
        definitions=(
            Definition(first, AppExpression(_app("f"))),
            Definition(second, NVariableExpression(first)),
        ),
    )

    result = NativeSolver().solve(
        NativeProgram(seeds=(Seed(_app("f"), Integer(7)),), rules=(rule,))
    )

    assert result.models[0].assignments == ("f(x)#=7", "h(x)#=7")


@pytest.mark.parametrize(
    "definitions",
    [
        lambda x, _y: (Definition(x, NVariableExpression(x)),),
        lambda x, y: (
            Definition(x, NVariableExpression(y)),
            Definition(y, NVariableExpression(x)),
        ),
    ],
)
def test_nstratification_cycles_have_location_aware_diagnostics(definitions: object) -> None:
    first = NVariable("_x")
    second = NVariable("_y")
    location = SourceLocation("cycle.aspf", 4, 7)
    build = cast("object", definitions)
    assert callable(build)
    rule = NativeRule(
        "cycle",
        AssignmentHead(_app("h"), ConstantExpression(Integer(1))),
        definitions=build(first, second),  # type: ignore[operator]
        location=location,
    )

    with pytest.raises(
        NativeValidationError,
        match=r"cycle\.aspf:4:7: non-Herbrand definitions are not n-stratified",
    ):
        NativeSolver().solve(NativeProgram(rules=(rule,)))


def test_missing_positive_definition_has_location_aware_diagnostic() -> None:
    variable = NVariable("_v")
    rule = NativeRule(
        "missing",
        AssignmentHead(_app("h"), NVariableExpression(variable)),
        location=SourceLocation("missing.aspf", 3, 12),
    )

    with pytest.raises(
        NativeValidationError,
        match=r"missing\.aspf:3:12: non-Herbrand variable _v has no positive definition",
    ):
        NativeSolver().solve(NativeProgram(rules=(rule,)))


def test_default_negation_is_failure_of_positive_satisfaction_for_undefined() -> None:
    source = AppExpression(_app("f"))
    value = ConstantExpression(Integer(5))
    program = NativeProgram(
        rules=(
            NativeRule(
                "not_eq",
                AtomHead(Atom("not_eq")),
                comparisons=(
                    Comparison(source, ComparisonOperator.EQUAL, value, default_negated=True),
                ),
            ),
            NativeRule(
                "not_ne",
                AtomHead(Atom("not_ne")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.NOT_EQUAL,
                        value,
                        default_negated=True,
                    ),
                ),
            ),
            NativeRule(
                "positive_eq",
                AtomHead(Atom("positive_eq")),
                comparisons=(Comparison(source, ComparisonOperator.EQUAL, value),),
            ),
            NativeRule(
                "positive_ne",
                AtomHead(Atom("positive_ne")),
                comparisons=(Comparison(source, ComparisonOperator.NOT_EQUAL, value),),
            ),
        )
    )

    result = NativeSolver().solve(program)

    assert result.models[0].visible == ("not_eq", "not_ne")


def test_equality_inequality_and_integer_ordering_control_visible_atoms() -> None:
    source = AppExpression(_app("f"))
    rules = tuple(
        NativeRule(
            identifier,
            AtomHead(Atom(identifier)),
            comparisons=(Comparison(source, operator, ConstantExpression(Integer(right))),),
        )
        for identifier, operator, right in (
            ("equal", ComparisonOperator.EQUAL, 5),
            ("not_equal", ComparisonOperator.NOT_EQUAL, 6),
            ("less", ComparisonOperator.LESS, 6),
            ("less_equal", ComparisonOperator.LESS_EQUAL, 5),
            ("greater", ComparisonOperator.GREATER, 4),
            ("greater_equal", ComparisonOperator.GREATER_EQUAL, 5),
        )
    )

    result = NativeSolver().solve(NativeProgram(seeds=(Seed(_app("f"), Integer(5)),), rules=rules))

    assert result.models[0].visible == (
        "equal",
        "f(x)#=5",
        "greater",
        "greater_equal",
        "less",
        "less_equal",
        "not_equal",
    )


def test_ordinary_variables_ground_before_rule_local_nvariables() -> None:
    ordinary = Variable("X")
    variable = NVariable("_v")
    item = Atom("item", (ordinary,))
    program = NativeProgram(
        facts=(Atom("item", (Symbol("a"),)), Atom("item", (Symbol("b"),))),
        seeds=(Seed(_app("f", ordinary), Integer(1), (item,)),),
        rules=(
            NativeRule(
                "per_item",
                AssignmentHead(_app("h", ordinary), NVariableExpression(variable)),
                definitions=(Definition(variable, AppExpression(_app("f", ordinary))),),
                when=(item,),
            ),
        ),
    )

    result = NativeSolver().solve(program)

    assert result.models[0].visible == (
        "f(a)#=1",
        "f(b)#=1",
        "h(a)#=1",
        "h(b)#=1",
        "item(a)",
        "item(b)",
    )
    assert result.theory_atoms == 4


def test_nvariables_are_rejected_in_application_and_ordinary_atom_arguments() -> None:
    forbidden = cast(Term, NVariable("_v"))
    location = SourceLocation("forbidden.aspf", 8, 9)

    with pytest.raises(
        NativeValidationError,
        match=r"forbidden\.aspf:8:9: non-Herbrand variables cannot occur in application",
    ):
        Application("balance", (forbidden,), location)
    with pytest.raises(
        NativeValidationError,
        match=r"forbidden\.aspf:8:9: non-Herbrand variables cannot occur in ordinary atom",
    ):
        Atom("p", (forbidden,), location)


def test_conservative_program_nloop_check_rejects_self_and_mutual_cycles() -> None:
    variable = NVariable("_v")
    self_rule = NativeRule(
        "self_loop",
        AssignmentHead(_app("f"), NVariableExpression(variable)),
        definitions=(Definition(variable, AppExpression(_app("f"))),),
        location=SourceLocation("loops.aspf", 2, 1),
    )
    with pytest.raises(
        NativeValidationError,
        match=r"loops\.aspf:2:1: conservative program-level n-loop rejection: f -> f",
    ):
        NativeSolver().solve(NativeProgram(rules=(self_rule,)))

    first = NativeRule(
        "first_loop",
        AssignmentHead(_app("f"), NVariableExpression(variable)),
        definitions=(Definition(variable, AppExpression(_app("g"))),),
        location=SourceLocation("loops.aspf", 5, 1),
    )
    second = NativeRule(
        "second_loop",
        AssignmentHead(_app("g"), NVariableExpression(variable)),
        definitions=(Definition(variable, AppExpression(_app("f"))),),
    )
    with pytest.raises(NativeValidationError, match="conservative program-level n-loop"):
        NativeSolver().solve(NativeProgram(rules=(first, second)))


def test_multiple_nvariables_rules_and_readers_remain_independent() -> None:
    first = NVariable("_first")
    second = NVariable("_second")
    program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(3)),),
        rules=(
            NativeRule(
                "two_variables",
                AssignmentHead(_app("h"), NVariableExpression(second)),
                definitions=(
                    Definition(first, AppExpression(_app("f"))),
                    Definition(second, NVariableExpression(first)),
                ),
            ),
            _copy_rule(identifier="other_reader", target=_app("k")),
        ),
    )

    result = NativeSolver().solve(program)

    assert result.models[0].assignments == ("f(x)#=3", "h(x)#=3", "k(x)#=3")


def test_repeated_solves_and_independent_solver_instances_are_deterministic() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 2),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(_copy_rule(),),
    )
    solver = NativeSolver()

    first = solver.solve(program)
    second = solver.solve(program)
    independent = NativeSolver().solve(program)

    assert [model.visible for model in first.models] == [model.visible for model in second.models]
    assert [model.visible for model in first.models] == [
        model.visible for model in independent.models
    ]
    assert first.undo_count > 0 and second.undo_count > 0 and independent.undo_count > 0


def test_unrelated_constants_do_not_become_candidate_values_or_leak_private_atoms() -> None:
    program = NativeProgram(
        facts=(Atom("unrelated", (Symbol("alpha"),)), Atom("unrelated", (Symbol("omega"),))),
        seeds=(Seed(_app("f"), Integer(5)),),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program)

    assert result.models[0].assignments == ("f(x)#=5", "h(x)#=5")
    assert all("aspf_native" not in atom for atom in result.models[0].visible)


def test_copy_models_are_exactly_equal_to_relational_reference_models() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 3),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(_copy_rule(),),
    )
    reference = """
    1 { choose(1..3) } 1.
    __bench_value(f(x),V) :- choose(V).
    __bench_value(h(x),V) :- __bench_value(f(x),V).
    """

    comparison = compare_with_reference(program, reference)

    assert comparison.equivalent
    assert len(comparison.native) == 3


def test_differential_matrix_compares_visible_semantics_not_private_atoms() -> None:
    source = AppExpression(_app("f"))
    five = ConstantExpression(Integer(5))
    defined_program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(5)),),
        rules=(
            NativeRule(
                "eq_visible",
                AtomHead(Atom("eq_visible")),
                comparisons=(Comparison(source, ComparisonOperator.EQUAL, five),),
            ),
            NativeRule(
                "ne_visible",
                AtomHead(Atom("ne_visible")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.NOT_EQUAL,
                        ConstantExpression(Integer(6)),
                    ),
                ),
            ),
            NativeRule(
                "lt_visible",
                AtomHead(Atom("lt_visible")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.LESS,
                        ConstantExpression(Integer(6)),
                    ),
                ),
            ),
        ),
    )
    defined_reference = """
    __bench_value(f(x),5).
    eq_visible :- __bench_value(f(x),5).
    ne_visible :- __bench_value(f(x),V), V != 6.
    lt_visible :- __bench_value(f(x),V), V < 6.
    """
    partial_program = NativeProgram(
        facts=(Atom("account", (X,)),),
        rules=(
            NativeRule(
                "not_eq_visible",
                AtomHead(Atom("not_eq_visible")),
                comparisons=(
                    Comparison(source, ComparisonOperator.EQUAL, five, default_negated=True),
                ),
            ),
            NativeRule(
                "not_ne_visible",
                AtomHead(Atom("not_ne_visible")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.NOT_EQUAL,
                        five,
                        default_negated=True,
                    ),
                ),
            ),
        ),
    )
    partial_reference = """
    account(x).
    not_eq_visible :- not __bench_value(f(x),5).
    not_ne_visible :- not __positive_ne.
    __positive_ne :- __bench_value(f(x),V), V != 5.
    """

    assert compare_with_reference(defined_program, defined_reference).equivalent
    assert compare_with_reference(partial_program, partial_reference).equivalent


def test_domain_safe_ordinary_variable_differential_models_match() -> None:
    ordinary = Variable("X")
    variable = NVariable("_v")
    item = Atom("item", (ordinary,))
    native = NativeProgram(
        facts=(Atom("item", (Symbol("a"),)), Atom("item", (Symbol("b"),))),
        seeds=(Seed(_app("f", ordinary), Integer(9), (item,)),),
        rules=(
            NativeRule(
                "domain_copy",
                AssignmentHead(_app("h", ordinary), NVariableExpression(variable)),
                definitions=(Definition(variable, AppExpression(_app("f", ordinary))),),
                when=(item,),
            ),
        ),
    )
    reference = """
    item(a;b).
    __bench_value(f(X),9) :- item(X).
    __bench_value(h(X),V) :- item(X), __bench_value(f(X),V).
    """

    assert compare_with_reference(native, reference).equivalent
