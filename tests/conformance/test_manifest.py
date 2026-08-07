from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_sources
from aspf_next.solver import SolveStatus, solve_program
from aspf_next.source import SourceText

CONFORMANCE_ROOT = Path(__file__).parent
MANIFEST_PATH = CONFORMANCE_ROOT / "manifest.json"
FIXTURE_ROOT = CONFORMANCE_ROOT / "fixtures"
REQUIRED_CATEGORIES = {
    "accepted-syntax",
    "rejected-syntax",
    "satisfiable",
    "unsatisfiable",
    "partiality",
    "functionality",
    "conditional-assignments",
    "multiple-models",
    "comments-layout",
    "multi-file",
}


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


MANIFEST = _load_manifest()
CASES: list[dict[str, Any]] = MANIFEST["cases"]


def _case_id(case: dict[str, Any]) -> str:
    return str(case["id"])


def _read_sources(case: dict[str, Any]) -> tuple[SourceText, ...]:
    return tuple(
        SourceText(
            (CONFORMANCE_ROOT / source_name).read_text(encoding="utf-8"),
            filename=source_name,
        )
        for source_name in case["sources"]
    )


def _normalized_models(models: list[dict[str, list[str]]]) -> set[tuple[tuple[str, ...], ...]]:
    return {(tuple(model["ordinary_atoms"]), tuple(model["assignments"])) for model in models}


def test_manifest_schema_and_fixture_coverage() -> None:
    assert MANIFEST["schema_version"] == 1
    assert CASES

    identifiers = [case["id"] for case in CASES]
    assert len(identifiers) == len(set(identifiers))
    assert {case["category"] for case in CASES} == REQUIRED_CATEGORIES

    referenced_sources: list[str] = []
    for case in CASES:
        assert case["sources"]
        assert case["category"] in REQUIRED_CATEGORIES
        for source_name in case["sources"]:
            assert source_name.startswith(f"fixtures/{case['category']}/")
            assert (CONFORMANCE_ROOT / source_name).is_file()
            referenced_sources.append(source_name)

        expected = case["expect"]
        assert expected["parse"] in {"accepted", "rejected"}
        assert "solve_status" in expected
        assert "model_count" in expected

        basis = case["source_basis"]
        assert basis["kind"] in {"historical-behavior", "aspf-next-boundary"}
        assert basis["references"]
        assert basis["notes"]

        if expected["parse"] == "rejected":
            assert expected["solve_status"] == "NOT_RUN"
            assert expected["model_count"] is None
            assert expected["diagnostic"]["source"] in case["sources"]
        else:
            assert expected["solve_status"] in {status.value for status in SolveStatus}
            assert isinstance(expected["model_count"], int)
            assert expected["model_count"] == len(expected["models"])

    fixture_sources = sorted(
        path.relative_to(CONFORMANCE_ROOT).as_posix() for path in FIXTURE_ROOT.rglob("*.aspf")
    )
    assert sorted(referenced_sources) == fixture_sources


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_conformance_case(case: dict[str, Any]) -> None:
    expected = case["expect"]
    sources = _read_sources(case)

    if expected["parse"] == "rejected":
        with pytest.raises(UnsupportedSyntaxError) as caught:
            parse_sources(sources)

        diagnostic = expected["diagnostic"]
        assert diagnostic["contains"] in caught.value.message
        assert caught.value.location.filename == diagnostic["source"]
        assert caught.value.location.line == diagnostic["line"]
        assert caught.value.location.column == diagnostic["column"]
        return

    program = parse_sources(sources)
    result = solve_program(program, models=0)

    assert result.status is SolveStatus(expected["solve_status"])
    assert result.exhausted
    assert len(result.models) == expected["model_count"]
    actual_models = {(model.ordinary_atoms, model.assignments) for model in result.models}
    assert actual_models == _normalized_models(expected["models"])
