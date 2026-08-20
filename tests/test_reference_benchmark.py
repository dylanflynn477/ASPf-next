from __future__ import annotations

from benchmarks.multi_application_workload import run_workload
from benchmarks.native_vs_reference import run_comparison
from benchmarks.reference_scaling import reference_source, run_reference
from benchmarks.solve_decomposition import run_decomposition


def test_reference_copy_has_linear_structural_overhead() -> None:
    result = run_reference((2, 4), repeats=1, warmups=0)

    assert [case.copy.model_count for case in result.cases] == [2, 4]
    assert [
        case.copy.structure.observer_rules - case.baseline.structure.observer_rules
        for case in result.cases
    ] == [2, 4]
    assert [
        case.copy.structure.symbolic_atoms - case.baseline.structure.symbolic_atoms
        for case in result.cases
    ] == [2, 4]


def test_reference_generator_rejects_nonpositive_domain() -> None:
    try:
        reference_source(0, include_copy=True)
    except ValueError as error:
        assert str(error) == "domain size must be positive"
    else:
        raise AssertionError("a nonpositive domain was accepted")


def test_native_copy_overhead_is_constant_and_models_match() -> None:
    result = run_comparison((2, 4), repeats=1, warmups=0)

    assert [
        case.reference_copy.structure.statistics_rules
        - case.reference_baseline.structure.statistics_rules
        for case in result.cases
    ] == [2, 4]
    assert [
        case.native_copy.structure.statistics_rules
        - case.native_baseline.structure.statistics_rules
        for case in result.cases
    ] == [1, 1]
    assert [
        case.native_copy.structure.theory_atoms - case.native_baseline.structure.theory_atoms
        for case in result.cases
    ] == [1, 1]
    assert all(case.model_equivalence.equivalent for case in result.cases)
    assert [case.native_copy.work.check_seed_probes for case in result.cases] == [0, 0]
    assert [case.native_copy.work.seed_activations for case in result.cases] == [2, 4]
    assert [case.native_copy.work.check_calls for case in result.cases] == [2, 4]
    assert [case.native_copy.work.rule_body_evaluations for case in result.cases] == [2, 4]
    assert [case.native_copy.work.application_decode_requests for case in result.cases] == [4, 6]
    assert [case.native_copy.work.decoded_applications for case in result.cases] == [2, 2]
    assert [case.native_copy.work.application_cache_hits for case in result.cases] == [2, 4]
    assert all(
        case.native_copy.propagator_init.median_seconds >= 0
        and case.native_copy.model_reconstruction.median_seconds >= 0
        for case in result.cases
    )


def test_solve_decomposition_preserves_modes_and_visible_equivalence() -> None:
    result = run_decomposition((2,), repeats=1, warmups=0)
    modes = {comparison.mode.name: comparison for comparison in result.cases[0].modes}

    assert modes["first-model"].native.model_count == 1
    assert modes["fixed-10"].native.model_count == 2
    assert modes["exhaustive-raw"].native.model_count == 2
    assert modes["exhaustive-visible"].native.model_count == 2
    assert modes["exhaustive-visible"].visible_models_equal
    assert modes["exhaustive-raw"].native.native_work is not None
    assert modes["exhaustive-raw"].native.native_work.snapshot_assignments == 0
    assert modes["exhaustive-visible"].native.native_reconstruction is not None


def test_multi_application_workload_smoke_preserves_partial_models() -> None:
    result = run_workload((3,), repeats=1, warmups=0)
    case = result.cases[0]

    assert case.reference.model_count == 3
    assert case.native.model_count == 3
    assert case.visible_models_equal
    assert case.reference_sha256 == case.native_sha256
    assert case.native.structure.theory_atoms == 21
    assert case.native.work.check_seed_probes == 0
    assert case.native.work.early_explanation_clauses > 0
    assert case.native.work.broad_blocking_clauses == 0
    assert case.native.work.maximum_clause_width <= 2
    assert case.native.work.clause_literals <= 5 * case.candidate_values
