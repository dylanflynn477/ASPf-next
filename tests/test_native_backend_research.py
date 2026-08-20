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
    DependencyEdgeKind,
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
    analyze_nloops,
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


def test_model_collection_can_be_disabled_without_changing_enumeration() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 3),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program, collect_models=False)

    assert result.satisfiable
    assert result.model_count == 3
    assert result.models == ()
    assert not result.models_collected
    assert result.model_reconstruction_seconds == 0
    assert result.snapshot_build_seconds == 0
    assert result.work_metrics.snapshot_assignments == 0
    assert result.work_metrics.ordinary_atoms == 0


def test_model_limit_and_detailed_reconstruction_profile_are_explicit() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 3),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program, model_limit=1, profile_reconstruction=True)

    assert result.model_count == 1
    assert len(result.models) == 1
    assert result.models_collected
    assert result.reconstruction_profile is not None
    assert result.reconstruction_profile.symbol_extraction_seconds >= 0
    assert result.reconstruction_profile.assignment_render_seconds >= 0
    assert result.reconstruction_profile.model_sort_seconds >= 0
    assert result.work_metrics.ordinary_atoms == 3
    assert result.work_metrics.ordinary_activations == 1

    with pytest.raises(ValueError, match="model limit must not be negative"):
        NativeSolver().solve(program, model_limit=-1)


def test_incremental_seed_index_does_not_rescan_the_candidate_domain() -> None:
    value = Variable("V")
    size = 40
    program = NativeProgram(
        choices=(Choice("choose", value, 1, size),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program)
    work = result.work_metrics

    assert len(result.models) == size
    assert work.seeds == size
    assert work.check_calls == size
    assert work.check_seed_probes == 0
    assert work.propagated_literals == size
    assert work.seed_activations == size
    assert work.seed_deactivations == size


def test_incremental_state_survives_a_blocked_conflict_branch() -> None:
    value = Variable("V")
    choose_value = Atom("choose", (value,))
    choose_one = Atom("choose", (Integer(1),))
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 2),),
        seeds=(
            Seed(_app("f"), value, (choose_value,)),
            Seed(_app("f"), Integer(99), (choose_one,)),
        ),
        rules=(_copy_rule(),),
    )

    result = NativeSolver().solve(program)

    assert [model.visible for model in result.models] == [("choose(2)", "f(x)#=2", "h(x)#=2")]
    assert result.work_metrics.blocking_clauses >= 1
    assert result.work_metrics.functionality_clauses >= 1
    assert result.work_metrics.broad_blocking_clauses == 0
    assert result.work_metrics.maximum_clause_width <= 2
    assert result.work_metrics.check_seed_probes == 0


def test_constant_seed_needs_no_watch_or_check_time_probe() -> None:
    result = NativeSolver().solve(
        NativeProgram(seeds=(Seed(_app("f"), Integer(5)),), rules=(_copy_rule(),))
    )

    assert result.models[0].assignments == ("f(x)#=5", "h(x)#=5")
    assert result.work_metrics.watched_literals == 0
    assert result.work_metrics.propagated_literals == 0
    assert result.work_metrics.check_seed_probes == 0


def test_dependency_queue_orders_a_reversed_assignment_chain_once() -> None:
    program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(5)),),
        rules=(
            _copy_rule(identifier="a_consumer", source=_app("g"), target=_app("h")),
            _copy_rule(identifier="z_provider", source=_app("f"), target=_app("g")),
        ),
    )

    result = NativeSolver().solve(program)

    assert result.models[0].assignments == ("f(x)#=5", "g(x)#=5", "h(x)#=5")
    assert result.work_metrics.rule_body_evaluations == 2


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

    native = NativeSolver().solve(program)
    assert not native.satisfiable
    assert native.work_metrics.functionality_clauses == 1
    assert native.work_metrics.broad_blocking_clauses == 0
    assert native.work_metrics.clause_literals == 0
    assert native.work_metrics.maximum_clause_width == 0


def test_constant_and_conditional_functionality_conflict_has_a_unit_reason() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 2),),
        seeds=(
            Seed(_app("f"), Integer(1)),
            Seed(_app("f"), Integer(2), (Atom("choose", (Integer(1),)),)),
        ),
    )

    result = NativeSolver().solve(program)

    assert [model.visible for model in result.models] == [("choose(2)", "f(x)#=1")]
    assert result.work_metrics.functionality_clauses == 1
    assert result.work_metrics.clause_literals == 1
    assert result.work_metrics.maximum_clause_width == 1


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
    assert result.work_metrics.blocking_clauses == 0


def test_unconditional_derived_functionality_conflict_has_an_empty_reason() -> None:
    program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(1)), Seed(_app("g"), Integer(2))),
        rules=(
            _copy_rule(identifier="from_f", source=_app("f"), target=_app("h")),
            _copy_rule(identifier="from_g", source=_app("g"), target=_app("h")),
        ),
    )

    result = NativeSolver().solve(program)

    assert not result.satisfiable
    assert result.work_metrics.functionality_clauses == 1
    assert result.work_metrics.derived_functionality_clauses == 1
    assert result.work_metrics.narrow_blocking_clauses == 1
    assert result.work_metrics.broad_blocking_clauses == 0
    assert result.work_metrics.clause_literals == 0


def test_conditional_derived_functionality_conflict_keeps_only_actual_supports() -> None:
    value = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 2),),
        seeds=(
            Seed(_app("f"), Integer(1), (Atom("choose", (Integer(1),)),)),
            Seed(_app("g"), Integer(2)),
        ),
        rules=(
            _copy_rule(identifier="from_f", source=_app("f"), target=_app("h")),
            _copy_rule(identifier="from_g", source=_app("g"), target=_app("h")),
        ),
    )

    result = NativeSolver().solve(program)

    assert [model.visible for model in result.models] == [("choose(2)", "g(x)#=2", "h(x)#=2")]
    assert result.work_metrics.derived_functionality_clauses == 1
    assert result.work_metrics.broad_blocking_clauses == 0
    assert result.work_metrics.maximum_clause_width == 1


def test_failed_required_equality_uses_a_narrow_guard_explanation() -> None:
    program = NativeProgram(
        seeds=(Seed(_app("f"), Integer(1)),),
        rules=(
            NativeRule(
                "required_equality",
                AtomHead(Atom("equal")),
                comparisons=(
                    Comparison(
                        AppExpression(_app("f")),
                        ComparisonOperator.EQUAL,
                        ConstantExpression(Integer(2)),
                    ),
                ),
            ),
        ),
    )

    result = NativeSolver().solve(program)

    assert result.models[0].visible == ("f(x)#=1",)
    assert result.work_metrics.functionality_clauses == 0
    assert result.work_metrics.guard_clauses == 1
    assert result.work_metrics.narrow_blocking_clauses == 1
    assert result.work_metrics.broad_blocking_clauses == 0
    assert result.work_metrics.maximum_clause_width == 1


def test_static_undefinedness_has_a_narrow_guard_explanation() -> None:
    program = NativeProgram(
        rules=(
            NativeRule(
                "missing_source",
                AtomHead(Atom("available")),
                comparisons=(
                    Comparison(
                        AppExpression(_app("missing")),
                        ComparisonOperator.EQUAL,
                        ConstantExpression(Integer(1)),
                    ),
                ),
            ),
        ),
    )

    result = NativeSolver().solve(program)

    assert result.models[0].visible == ()
    assert result.work_metrics.guard_clauses == 1
    assert result.work_metrics.broad_blocking_clauses == 0
    assert result.work_metrics.maximum_clause_width == 1


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


def test_program_nloop_screen_rejects_self_and_mutual_cycles() -> None:
    variable = NVariable("_v")
    self_rule = NativeRule(
        "self_loop",
        AssignmentHead(_app("f"), NVariableExpression(variable)),
        definitions=(Definition(variable, AppExpression(_app("f"))),),
        location=SourceLocation("loops.aspf", 2, 1),
    )
    with pytest.raises(
        NativeValidationError,
        match=(
            r"loops\.aspf:2:1: historical n-loop rejected: positive dependency path "
            r"f\(x\)#=_v -> _v#=f\(x\) shares simple term f\(x\)"
        ),
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
    with pytest.raises(NativeValidationError, match="historical n-loop rejected"):
        NativeSolver().solve(NativeProgram(rules=(first, second)))


def test_nloop_analysis_distinguishes_full_simple_terms_and_negative_edges() -> None:
    f_a = Application("f", (Symbol("a"),))
    f_b = Application("f", (Symbol("b"),))
    distinct_key = NativeRule(
        "distinct_key",
        AssignmentHead(f_a, ConstantExpression(Integer(2))),
        comparisons=(
            Comparison(
                AppExpression(f_b),
                ComparisonOperator.NOT_EQUAL,
                ConstantExpression(Integer(3)),
            ),
        ),
    )
    default_negated = NativeRule(
        "negative_edge",
        AssignmentHead(f_a, ConstantExpression(Integer(2))),
        comparisons=(
            Comparison(
                AppExpression(f_a),
                ComparisonOperator.NOT_EQUAL,
                ConstantExpression(Integer(3)),
                default_negated=True,
            ),
        ),
    )

    distinct_analysis = analyze_nloops(NativeProgram(rules=(distinct_key,)))
    negative_analysis = analyze_nloops(NativeProgram(rules=(default_negated,)))

    assert distinct_analysis.exact_for_ground_program
    assert distinct_analysis.loop is None
    assert negative_analysis.exact_for_ground_program
    assert negative_analysis.loop is None


def test_direct_nloop_reports_typed_positive_edge_and_source_provenance() -> None:
    location = SourceLocation("direct-loop.aspf", 7, 3)
    application = Application("f", (Symbol("a"),))
    program = NativeProgram(
        rules=(
            NativeRule(
                "direct",
                AssignmentHead(application, ConstantExpression(Integer(2))),
                comparisons=(
                    Comparison(
                        AppExpression(application),
                        ComparisonOperator.NOT_EQUAL,
                        ConstantExpression(Integer(3)),
                    ),
                ),
                location=location,
            ),
        )
    )

    analysis = analyze_nloops(program)

    assert analysis.exact_for_ground_program
    assert analysis.loop is not None
    assert analysis.loop.seed.location == location
    assert analysis.loop.shared_terms == (application,)
    assert [edge.kind for edge in analysis.loop.edges] == [DependencyEdgeKind.POSITIVE_BODY]
    with pytest.raises(
        NativeValidationError,
        match=(
            r"direct-loop\.aspf:7:3: historical n-loop rejected: positive dependency "
            r"path f\(a\)#=2 -> f\(a\)#!=3 shares simple term f\(a\)"
        ),
    ):
        NativeSolver().solve(program)


def test_indirect_nloop_crosses_an_ordinary_positive_dependency() -> None:
    application = Application("f", (Symbol("a"),))
    p = Atom("p")
    program = NativeProgram(
        rules=(
            NativeRule(
                "assignment",
                AssignmentHead(application, ConstantExpression(Integer(2))),
                when=(p,),
            ),
            NativeRule(
                "ordinary",
                AtomHead(p),
                comparisons=(
                    Comparison(
                        AppExpression(application),
                        ComparisonOperator.NOT_EQUAL,
                        ConstantExpression(Integer(3)),
                    ),
                ),
            ),
        )
    )

    analysis = analyze_nloops(program)

    assert analysis.loop is not None
    assert [node.label for node in analysis.loop.path] == [
        "f(a)#=2",
        "p",
        "p",
        "f(a)#!=3",
    ]
    assert [edge.kind for edge in analysis.loop.edges] == [
        DependencyEdgeKind.POSITIVE_BODY,
        DependencyEdgeKind.LITERAL_MATCH,
        DependencyEdgeKind.POSITIVE_BODY,
    ]


def test_ordinary_asp_recursion_is_not_an_nloop() -> None:
    p = Atom("p")
    q = Atom("q")
    program = NativeProgram(
        rules=(
            NativeRule("p_from_q", AtomHead(p), when=(q,)),
            NativeRule("q_from_p", AtomHead(q), when=(p,)),
        )
    )

    analysis = analyze_nloops(program)

    assert analysis.exact_for_ground_program
    assert analysis.loop is None


def test_non_ground_nloop_analysis_is_explicitly_conservative() -> None:
    variable = Variable("X")
    item = Atom("item", (variable,))
    application = Application("f", (variable,))
    program = NativeProgram(
        rules=(
            NativeRule(
                "potential_loop",
                AssignmentHead(application, ConstantExpression(Integer(2))),
                comparisons=(
                    Comparison(
                        AppExpression(Application("f", (Symbol("a"),))),
                        ComparisonOperator.NOT_EQUAL,
                        ConstantExpression(Integer(3)),
                    ),
                ),
                when=(item,),
            ),
        )
    )

    analysis = analyze_nloops(program)

    assert not analysis.exact_for_ground_program
    assert analysis.loop is not None


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


def test_dependency_diamond_with_two_nvariables_backtracks_without_stale_values() -> None:
    value = Variable("V")
    choose = Atom("choose", (value,))
    left = NVariable("_left")
    right = NVariable("_right")
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 6),),
        seeds=(Seed(_app("f"), value, (choose,)),),
        rules=(
            _copy_rule(identifier="left_arm", source=_app("f"), target=_app("g")),
            _copy_rule(identifier="right_arm", source=_app("f"), target=_app("h")),
            NativeRule(
                "join",
                AssignmentHead(_app("k"), NVariableExpression(left)),
                definitions=(
                    Definition(left, AppExpression(_app("g"))),
                    Definition(right, AppExpression(_app("h"))),
                ),
                comparisons=(
                    Comparison(
                        NVariableExpression(left),
                        ComparisonOperator.EQUAL,
                        NVariableExpression(right),
                    ),
                ),
            ),
        ),
    )

    result = NativeSolver().solve(program)

    assert result.model_count == 6
    for expected, model in enumerate(result.models, start=1):
        assert model.assignments == (
            f"f(x)#={expected}",
            f"g(x)#={expected}",
            f"h(x)#={expected}",
            f"k(x)#={expected}",
        )
    assert result.work_metrics.seed_activations == result.work_metrics.seed_deactivations
    assert result.work_metrics.check_seed_probes == 0


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


def test_two_thread_copy_enumeration_matches_single_thread_and_restores_state() -> None:
    value = Variable("V")
    choose = Atom("choose", (value,))
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 20),),
        seeds=(
            Seed(_app("f"), value, (choose,)),
            Seed(_app("g"), value, (choose,)),
        ),
        rules=(
            _copy_rule(identifier="copy_f", source=_app("f"), target=_app("h")),
            _copy_rule(identifier="copy_g", source=_app("g"), target=_app("k")),
        ),
    )

    single = NativeSolver().solve(program, threads=1)
    parallel = NativeSolver().solve(program, threads=2)
    repeated = NativeSolver().solve(program, threads=2)

    assert parallel.solver_threads == 2
    assert parallel.model_count == 20
    assert [model.visible for model in parallel.models] == [
        model.visible for model in single.models
    ]
    assert [model.visible for model in repeated.models] == [
        model.visible for model in single.models
    ]
    assert parallel.work_metrics.seed_activations == parallel.work_metrics.seed_deactivations
    assert repeated.work_metrics.seed_activations == repeated.work_metrics.seed_deactivations


def test_two_thread_explained_guards_match_single_thread_repeatedly() -> None:
    value = Variable("V")
    source = AppExpression(_app("f"))
    program = NativeProgram(
        choices=(Choice("choose", value, 1, 20),),
        seeds=(Seed(_app("f"), value, (Atom("choose", (value,)),)),),
        rules=(
            NativeRule(
                "high",
                AtomHead(Atom("high")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.GREATER_EQUAL,
                        ConstantExpression(Integer(10)),
                    ),
                ),
            ),
        ),
    )

    single = NativeSolver().solve(program, threads=1)
    parallel = NativeSolver().solve(program, threads=2)
    repeated = NativeSolver().solve(program, threads=2)

    assert [model.visible for model in parallel.models] == [
        model.visible for model in single.models
    ]
    assert [model.visible for model in repeated.models] == [
        model.visible for model in single.models
    ]
    assert parallel.work_metrics.broad_blocking_clauses == 0
    assert repeated.work_metrics.broad_blocking_clauses == 0
    assert parallel.work_metrics.evaluation_cache_hits > 0
    assert repeated.work_metrics.evaluation_cache_hits > 0
    assert parallel.work_metrics.maximum_clause_width <= 2
    assert repeated.work_metrics.maximum_clause_width <= 2


def test_thread_count_is_bounded_to_the_evaluated_research_modes() -> None:
    with pytest.raises(ValueError, match="thread count must be 1 or 2"):
        NativeSolver().solve(NativeProgram(), threads=0)
    with pytest.raises(ValueError, match="thread count must be 1 or 2"):
        NativeSolver().solve(NativeProgram(), threads=3)


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
