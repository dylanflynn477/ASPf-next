from __future__ import annotations

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
