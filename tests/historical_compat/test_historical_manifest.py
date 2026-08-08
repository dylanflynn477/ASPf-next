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
    if case["disposition"] == "passing":
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
        assert case["expected_diagnostic"] in str(caught.value)
        return

    result = solve_program(parse_program(source, filename=str(source_path)), models=0)
    assert result.status is SolveStatus.SATISFIABLE
    actual_models = {(model.ordinary_atoms, model.assignments) for model in result.models}
    expected_models = {
        (tuple(model["ordinary_atoms"]), tuple(model["assignments"]))
        for model in case["expected_models"]
    }
    assert actual_models == expected_models


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
