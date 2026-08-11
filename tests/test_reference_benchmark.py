from __future__ import annotations

from benchmarks.native_vs_reference import run_comparison
from benchmarks.reference_scaling import reference_source, run_reference


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
    assert all(
        case.native_copy.propagator_init.median_seconds >= 0
        and case.native_copy.model_reconstruction.median_seconds >= 0
        for case in result.cases
    )
