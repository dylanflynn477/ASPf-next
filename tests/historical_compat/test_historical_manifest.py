from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program
from aspf_next.solver import SolveStatus, solve_program

ROOT = Path(__file__).parent
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
CASES: list[dict[str, Any]] = MANIFEST["cases"]


def _parameter(case: dict[str, Any]) -> pytest.ParameterSet:
    if case["disposition"] != "xfail":
        return pytest.param(case, id=case["id"])
    reason = f"{case['expected_aspf_next_status']}: {case['semantic_notes']}"
    return pytest.param(case, id=case["id"], marks=pytest.mark.xfail(reason=reason, strict=True))


@pytest.mark.parametrize("case", [_parameter(case) for case in CASES])
def test_historical_case(case: dict[str, Any]) -> None:
    source_path = ROOT / case["source"]
    source = source_path.read_text(encoding="utf-8")

    if case["expected_historical_status"] == "invalid":
        with pytest.raises(UnsupportedSyntaxError) as caught:
            parse_program(source, filename=str(source_path))
        _assert_expected_diagnostic(caught.value, case["expected_diagnostic"])
        return

    if case["disposition"] == "intentionally-deferred":
        with pytest.raises(UnsupportedSyntaxError) as caught:
            parse_program(source, filename=str(source_path))
        _assert_expected_diagnostic(caught.value, case["expected_diagnostic"])
        pytest.xfail(f"intentionally deferred: {case['semantic_notes']}")
        return

    result = solve_program(parse_program(source, filename=str(source_path)), models=0)
    assert result.status is SolveStatus.SATISFIABLE
    actual_models = {(model.ordinary_atoms, model.assignments) for model in result.models}
    expected_models = {
        (tuple(model["ordinary_atoms"]), tuple(model["assignments"]))
        for model in case["expected_models"]
    }
    assert actual_models == expected_models


def _assert_expected_diagnostic(error: UnsupportedSyntaxError, diagnostic: dict[str, Any]) -> None:
    assert diagnostic["contains"] in error.message
    assert error.location.line == diagnostic["line"]
    assert error.location.column == diagnostic["column"]


def test_manifest_metadata_is_complete_and_unique() -> None:
    required = {
        "id",
        "feature",
        "source",
        "primary_source_origin",
        "expected_historical_status",
        "baseline_aspf_next_status",
        "expected_aspf_next_status",
        "disposition",
        "expected_models",
        "semantic_notes",
        "compatibility_tier",
    }
    identifiers = [case["id"] for case in CASES]

    assert len(identifiers) == len(set(identifiers))
    assert all(required <= case.keys() for case in CASES)
    assert all((ROOT / case["source"]).is_file() for case in CASES)
    assert all(
        case["disposition"] in {"passing", "xfail", "intentionally-deferred"} for case in CASES
    )
    for case in CASES:
        if case["expected_historical_status"] == "invalid":
            assert case["disposition"] == "passing"
            assert case["expected_aspf_next_status"] == "rejected"
            assert _valid_diagnostic(case.get("expected_diagnostic"))
        if case["disposition"] == "intentionally-deferred":
            assert case["expected_historical_status"] == "valid"
            assert case["expected_aspf_next_status"] == "unsupported"
            assert _valid_diagnostic(case.get("expected_diagnostic"))
        if case["disposition"] == "xfail":
            assert case["expected_aspf_next_status"] == "unresolved"


def _valid_diagnostic(value: object) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("contains"), str)
        and isinstance(value.get("line"), int)
        and isinstance(value.get("column"), int)
    )
