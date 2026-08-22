from __future__ import annotations

from itertools import product

import pytest

from research.native_backend import (
    AppExpression,
    Application,
    AssignmentHead,
    Atom,
    AtomHead,
    Choice,
    ClauseAuditKind,
    Comparison,
    ComparisonOperator,
    ConstantExpression,
    Definition,
    Integer,
    NativeProgram,
    NativeRule,
    NativeSolver,
    NVariable,
    NVariableExpression,
    Seed,
    Symbol,
    Variable,
)
from research.native_backend.differential import compare_with_reference

X = Symbol("x")


def _app(function: str) -> Application:
    return Application(function, (X,))


def _copy(identifier: str, source: str, target: str) -> NativeRule:
    variable = NVariable("_value")
    return NativeRule(
        identifier,
        AssignmentHead(_app(target), NVariableExpression(variable)),
        definitions=(Definition(variable, AppExpression(_app(source))),),
    )


def _visible(program: NativeProgram, *, threads: int = 1) -> tuple[tuple[str, ...], ...]:
    return tuple(model.visible for model in NativeSolver().solve(program, threads=threads).models)


def _without_noise(models: tuple[tuple[str, ...], ...]) -> set[tuple[str, ...]]:
    return {tuple(atom for atom in model if not atom.startswith("noise(")) for model in models}


def _independent_paths_program(
    *,
    reverse_seeds: bool = False,
    reverse_rules: bool = False,
    renamed: bool = False,
    noise: bool = False,
) -> NativeProgram:
    left = Variable("L")
    right = Variable("R")
    seeds = (
        Seed(_app("f"), Integer(7), (Atom("left", (Integer(1),)),)),
        Seed(_app("g"), Integer(7), (Atom("right", (Integer(1),)),)),
    )
    copies = (
        _copy("alpha" if renamed else "from_f", "f", "h"),
        _copy("omega" if renamed else "from_g", "g", "h"),
    )
    source = AppExpression(_app("h"))
    guards = (
        NativeRule(
            "present_renamed" if renamed else "present",
            AtomHead(Atom("present")),
            comparisons=(
                Comparison(
                    source,
                    ComparisonOperator.EQUAL,
                    ConstantExpression(Integer(7)),
                ),
            ),
        ),
        NativeRule(
            "absent_renamed" if renamed else "absent",
            AtomHead(Atom("absent")),
            comparisons=(
                Comparison(
                    source,
                    ComparisonOperator.EQUAL,
                    ConstantExpression(Integer(7)),
                    default_negated=True,
                ),
            ),
        ),
    )
    choices = [Choice("left", left, 0, 1), Choice("right", right, 0, 1)]
    if noise:
        choices.append(Choice("noise", Variable("N"), 0, 1))
    return NativeProgram(
        choices=tuple(choices),
        seeds=tuple(reversed(seeds)) if reverse_seeds else seeds,
        rules=(
            *(tuple(reversed(copies)) if reverse_rules else copies),
            *guards,
        ),
    )


INDEPENDENT_PATHS_REFERENCE = """
1 { left(0..1) } 1.
1 { right(0..1) } 1.
__bench_value(f(x),7) :- left(1).
__bench_value(g(x),7) :- right(1).
__bench_value(h(x),V) :- __bench_value(f(x),V).
__bench_value(h(x),V) :- __bench_value(g(x),V).
present :- __bench_value(h(x),7).
absent :- not __present_h.
__present_h :- __bench_value(h(x),7).
:- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.
"""


def test_independent_same_value_paths_are_differentially_exact_and_metamorphic() -> None:
    baseline = _independent_paths_program()
    baseline_result = NativeSolver().solve(baseline)
    baseline_models = tuple(model.visible for model in baseline_result.models)

    assert compare_with_reference(baseline, INDEPENDENT_PATHS_REFERENCE).equivalent
    assert len(baseline_models) == 4

    for reverse_seeds, reverse_rules, renamed in product((False, True), repeat=3):
        variant = _independent_paths_program(
            reverse_seeds=reverse_seeds,
            reverse_rules=reverse_rules,
            renamed=renamed,
        )
        assert _visible(variant) == baseline_models
        assert _visible(variant, threads=2) == baseline_models

    noisy = _independent_paths_program(noise=True)
    noisy_result = NativeSolver().solve(noisy)
    assert _without_noise(tuple(model.visible for model in noisy_result.models)) == set(
        baseline_models
    )
    assert noisy_result.work_metrics.maximum_clause_width == (
        baseline_result.work_metrics.maximum_clause_width
    )

    audited = NativeSolver().solve(noisy, audit_clauses=True)
    assert baseline_result.clause_audits == ()
    assert audited.clause_audits
    assert audited.work_metrics.broad_blocking_clauses == 0
    assert audited.work_metrics.dynamic_undefined_analysis_runs > 0
    assert audited.work_metrics.dynamic_undefined_applications_proven > 0
    for audit in audited.clause_audits:
        assert audit.kind is ClauseAuditKind.GUARD
        assert audit.locked
        assert 1 <= len(audit.support_literals) <= 2
        assert all(
            description.removeprefix("not ").startswith("seed:") and "noise" not in description
            for origin in audit.support_origins
            for description in origin.descriptions
        )
        if any(literal < 0 for literal in audit.support_literals):
            assert len(audit.support_literals) == 2
            assert {
                description
                for origin in audit.support_origins
                for description in origin.descriptions
            } == {"not seed:f(x)#=7", "not seed:g(x)#=7"}
        expected_clause = {-literal for literal in audit.support_literals}
        if audit.required_literal is not None and abs(audit.required_literal) > 1:
            expected_clause.add(audit.required_literal)
        assert audit.clause == tuple(sorted(expected_clause))


def _transition_program(*, reverse_seeds: bool = False) -> NativeProgram:
    mode = Variable("M")
    seeds = (
        Seed(_app("f"), Integer(1), (Atom("mode", (Integer(1),)),)),
        Seed(_app("f"), Integer(1), (Atom("mode", (Integer(3),)),)),
        Seed(_app("f"), Integer(2), (Atom("mode", (Integer(3),)),)),
        Seed(_app("f"), Integer(1), (Atom("mode", (Integer(4),)),)),
    )
    source = AppExpression(_app("h"))
    return NativeProgram(
        choices=(Choice("mode", mode, 1, 4),),
        seeds=tuple(reversed(seeds)) if reverse_seeds else seeds,
        rules=(
            _copy("copy", "f", "h"),
            NativeRule(
                "is_one",
                AtomHead(Atom("is_one")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.EQUAL,
                        ConstantExpression(Integer(1)),
                    ),
                ),
            ),
            NativeRule(
                "not_one",
                AtomHead(Atom("not_one")),
                comparisons=(
                    Comparison(
                        source,
                        ComparisonOperator.EQUAL,
                        ConstantExpression(Integer(1)),
                        default_negated=True,
                    ),
                ),
            ),
        ),
    )


TRANSITION_REFERENCE = """
1 { mode(1..4) } 1.
__bench_value(f(x),1) :- mode(1).
__bench_value(f(x),1) :- mode(3).
__bench_value(f(x),2) :- mode(3).
__bench_value(f(x),1) :- mode(4).
__bench_value(h(x),V) :- __bench_value(f(x),V).
is_one :- __bench_value(h(x),1).
not_one :- not __h_is_one.
__h_is_one :- __bench_value(h(x),1).
:- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.
"""


def test_defined_undefined_conflict_defined_transitions_restore_exact_state() -> None:
    baseline = _transition_program()
    expected = compare_with_reference(baseline, TRANSITION_REFERENCE)

    assert expected.equivalent
    assert len(expected.native) == 3
    assert all("mode(3)" not in model for model in expected.native)

    for program in (baseline, _transition_program(reverse_seeds=True)):
        single = NativeSolver().solve(program)
        parallel = NativeSolver().solve(program, threads=2)
        repeated = NativeSolver().solve(program, threads=2)
        assert tuple(model.visible for model in single.models) == expected.native
        assert tuple(model.visible for model in parallel.models) == expected.native
        assert tuple(model.visible for model in repeated.models) == expected.native
        assert single.work_metrics.seed_activations == single.work_metrics.seed_deactivations
        assert parallel.work_metrics.seed_activations == parallel.work_metrics.seed_deactivations
        assert repeated.work_metrics.seed_activations == repeated.work_metrics.seed_deactivations

    audited = NativeSolver().solve(baseline, audit_clauses=True)
    assert audited.work_metrics.broad_blocking_clauses == 0
    assert audited.work_metrics.dynamic_undefined_analysis_runs > 0
    assert any(
        audit.kind is ClauseAuditKind.SEED_FUNCTIONALITY
        and {origin.literal for origin in audit.support_origins} == set(audit.support_literals)
        for audit in audited.clause_audits
    )
    assert any(
        audit.kind is ClauseAuditKind.GUARD
        and all(literal < 0 for literal in audit.support_literals)
        and all(
            description.startswith("not seed:f(x)#=")
            for origin in audit.support_origins
            for description in origin.descriptions
        )
        for audit in audited.clause_audits
    )


def _comparison_program(*, reverse_rules: bool = False) -> NativeProgram:
    left = Variable("L")
    right = Variable("R")
    first = NVariable("_first")
    second = NVariable("_second")
    f = AppExpression(_app("f"))
    g = AppExpression(_app("g"))
    rules = (
        NativeRule(
            "same",
            AtomHead(Atom("same")),
            comparisons=(Comparison(f, ComparisonOperator.EQUAL, g),),
        ),
        NativeRule(
            "different",
            AtomHead(Atom("different")),
            comparisons=(Comparison(f, ComparisonOperator.EQUAL, g, default_negated=True),),
        ),
        NativeRule(
            "ordered",
            AtomHead(Atom("ordered")),
            comparisons=(Comparison(f, ComparisonOperator.LESS, g),),
        ),
        NativeRule(
            "two_nvariables",
            AtomHead(Atom("nvariables_same")),
            definitions=(
                Definition(first, f),
                Definition(second, g),
            ),
            comparisons=(
                Comparison(
                    NVariableExpression(first),
                    ComparisonOperator.EQUAL,
                    NVariableExpression(second),
                ),
            ),
        ),
        NativeRule(
            "agreeing_definitions",
            AtomHead(Atom("agreeing_definitions")),
            definitions=(Definition(first, f), Definition(first, g)),
        ),
    )
    return NativeProgram(
        choices=(Choice("left", left, 0, 1), Choice("right", right, 0, 1)),
        seeds=(
            Seed(_app("f"), left, (Atom("left", (left,)),)),
            Seed(_app("g"), right, (Atom("right", (right,)),)),
        ),
        rules=tuple(reversed(rules)) if reverse_rules else rules,
    )


COMPARISON_REFERENCE = """
1 { left(0..1) } 1.
1 { right(0..1) } 1.
__bench_value(f(x),L) :- left(L).
__bench_value(g(x),R) :- right(R).
same :- __bench_value(f(x),V), __bench_value(g(x),V).
different :- not __same.
__same :- __bench_value(f(x),V), __bench_value(g(x),V).
ordered :- __bench_value(f(x),L), __bench_value(g(x),R), L < R.
nvariables_same :- __bench_value(f(x),V), __bench_value(g(x),V).
agreeing_definitions :- __bench_value(f(x),V), __bench_value(g(x),V).
:- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.
"""


def test_operand_provenance_multiple_nvariables_and_definitions_are_exact() -> None:
    baseline = _comparison_program()
    result = NativeSolver().solve(baseline, audit_clauses=True)

    assert compare_with_reference(baseline, COMPARISON_REFERENCE).equivalent
    assert _visible(_comparison_program(reverse_rules=True)) == tuple(
        model.visible for model in result.models
    )
    assert result.work_metrics.broad_blocking_clauses == 0
    assert result.work_metrics.maximum_clause_width <= 3
    assert result.clause_audits
    for audit in result.clause_audits:
        assert audit.kind is ClauseAuditKind.GUARD
        assert len(audit.support_literals) == 2
        descriptions = {
            description for origin in audit.support_origins for description in origin.descriptions
        }
        assert any(description.startswith("seed:f(x)#=") for description in descriptions)
        assert any(description.startswith("seed:g(x)#=") for description in descriptions)


def test_derived_functionality_audit_contains_only_two_conflicting_paths() -> None:
    choice = Variable("V")
    program = NativeProgram(
        choices=(Choice("choose", choice, 1, 2),),
        seeds=(
            Seed(_app("f"), Integer(1), (Atom("choose", (Integer(1),)),)),
            Seed(_app("g"), Integer(2)),
        ),
        rules=(
            _copy("from_f", "f", "h"),
            _copy("from_g", "g", "h"),
        ),
    )

    result = NativeSolver().solve(program, audit_clauses=True)

    conflicts = [
        audit
        for audit in result.clause_audits
        if audit.kind is ClauseAuditKind.DERIVED_FUNCTIONALITY
    ]
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.target == "h(x):1!=2"
    assert len(conflict.support_literals) == 1
    assert {
        description for origin in conflict.support_origins for description in origin.descriptions
    } == {"seed:f(x)#=1"}
    assert conflict.clause == tuple(-literal for literal in conflict.support_literals)


def test_clause_audit_rejects_nondeterministic_parallel_collection() -> None:
    with pytest.raises(ValueError, match="auditing requires deterministic one-thread"):
        NativeSolver().solve(_independent_paths_program(), threads=2, audit_clauses=True)


def _comparison_matrix_case(
    left_value: int | None,
    right_value: int | None,
    operator: ComparisonOperator,
    default_negated: bool,
    nvariable_count: int,
) -> tuple[NativeProgram, str]:
    seeds = []
    reference_facts = []
    if left_value is not None:
        seeds.append(Seed(_app("f"), Integer(left_value)))
        reference_facts.append(f"__bench_value(f(x),{left_value}).")
    if right_value is not None:
        seeds.append(Seed(_app("g"), Integer(right_value)))
        reference_facts.append(f"__bench_value(g(x),{right_value}).")

    definitions: list[Definition] = []
    left_expression = AppExpression(_app("f"))
    right_expression = AppExpression(_app("g"))
    if nvariable_count >= 1:
        first = NVariable("_first")
        definitions.append(Definition(first, left_expression))
        left_expression = NVariableExpression(first)
    if nvariable_count >= 2:
        second = NVariable("_second")
        definitions.append(Definition(second, right_expression))
        right_expression = NVariableExpression(second)
    if nvariable_count >= 3:
        third = NVariable("_third")
        definitions.append(Definition(third, left_expression))
        left_expression = NVariableExpression(third)

    native = NativeProgram(
        seeds=tuple(seeds),
        rules=(
            NativeRule(
                "holds",
                AtomHead(Atom("holds")),
                definitions=tuple(definitions),
                comparisons=(
                    Comparison(
                        left_expression,
                        operator,
                        right_expression,
                        default_negated=default_negated,
                    ),
                ),
            ),
        ),
    )

    definition_atoms: list[str] = []
    if nvariable_count >= 1:
        definition_atoms.append("__bench_value(f(x),V0)")
    if nvariable_count >= 2:
        definition_atoms.append("__bench_value(g(x),V1)")
    left_term = "V0" if nvariable_count >= 1 else "L"
    right_term = "V1" if nvariable_count >= 2 else "R"
    comparison_atoms = list(definition_atoms)
    if nvariable_count == 0:
        comparison_atoms.extend(("__bench_value(f(x),L)", "__bench_value(g(x),R)"))
    elif nvariable_count == 1:
        comparison_atoms.append("__bench_value(g(x),R)")
    symbol = "=" if operator is ComparisonOperator.EQUAL else "!="
    comparison_atoms.append(f"{left_term} {symbol} {right_term}")

    if default_negated:
        arguments = ",".join(f"V{index}" for index in range(min(nvariable_count, 2)))
        helper = f"__positive({arguments})" if arguments else "__positive"
        outer = [*definition_atoms, f"not {helper}"]
        reference_rule = f"holds :- {', '.join(outer)}."
        helper_rule = f"{helper} :- {', '.join(comparison_atoms)}."
    else:
        reference_rule = f"holds :- {', '.join(comparison_atoms)}."
        helper_rule = ""
    reference = "\n".join(
        (
            *reference_facts,
            reference_rule,
            helper_rule,
            ":- __bench_value(K,V1), __bench_value(K,V2), V1 != V2.",
        )
    )
    return native, reference


@pytest.mark.parametrize(
    ("left_value", "right_value", "operator", "default_negated", "nvariable_count"),
    [
        (left, right, operator, negated, count)
        for left, right, operator, negated, count in product(
            (None, 0, 1),
            (None, 0, 1),
            (ComparisonOperator.EQUAL, ComparisonOperator.NOT_EQUAL),
            (False, True),
            range(4),
        )
    ],
)
def test_exhaustive_small_comparison_and_nvariable_matrix_matches_reference(
    left_value: int | None,
    right_value: int | None,
    operator: ComparisonOperator,
    default_negated: bool,
    nvariable_count: int,
) -> None:
    native, reference = _comparison_matrix_case(
        left_value,
        right_value,
        operator,
        default_negated,
        nvariable_count,
    )

    comparison = compare_with_reference(native, reference)

    assert comparison.equivalent
