from __future__ import annotations

import json
from pathlib import Path

import pytest

from aspf_next.cli import main


def write_program(tmp_path: Path, source: str, name: str = "input.aspf") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_human_output_hides_internal_predicates(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    path = write_program(
        tmp_path,
        "#nherb balance/1.\nbalance(account1) #= 500.\nsolvent :- balance(account1) #= 500.\n",
    )

    assert main([str(path)]) == 0
    output = capsys.readouterr().out
    assert "solvent balance(account1)#=500" in output
    assert "__aspf_" not in output
    assert output.endswith("SATISFIABLE\n")


def test_emit_lowered_prints_reference_translation(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    path = write_program(tmp_path, "#nherb balance/1.\nbalance(a) #= 1.\n")

    assert main([str(path), "--emit-lowered"]) == 0
    output = capsys.readouterr().out
    assert "__aspf_value(balance(a),1)." in output
    assert "V1 != V2" in output


def test_emit_lowered_prints_definedness_aware_not_equal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_program(
        tmp_path,
        "#nherb balance/1.\ndifferent :- balance(a) #!= 1.\n",
    )

    assert main([str(path), "--emit-lowered"]) == 0
    output = capsys.readouterr().out
    assert "__aspf_value(balance(a),_AspfNeq0)" in output
    assert "_AspfNeq0 != 1" in output
    assert "not __aspf_value" not in output


def test_not_equal_human_and_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_program(
        tmp_path,
        "#nherb balance/1.\nbalance(a) #= 2.\ndifferent :- balance(a) #!= 1.\n",
    )

    assert main([str(path)]) == 0
    human = capsys.readouterr().out
    assert "different balance(a)#=2" in human
    assert "__aspf_" not in human

    assert main([str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["models"][0]["ordinary_atoms"] == ["different"]
    assert payload["models"][0]["assignments"] == ["balance(a)#=2"]


def test_cli_rejects_not_equal_rule_head_with_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_program(
        tmp_path,
        "#nherb balance/1.\nbalance(a) #!= 1.\n",
        "head.aspf",
    )

    assert main([str(path)]) == 2
    error = capsys.readouterr().err
    assert f"{path}:2:12" in error
    assert "only as a complete positive rule-body literal" in error


def test_json_enumerates_all_models(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    path = write_program(tmp_path, "1 { selected(a); selected(b) } 1.\n")

    assert main([str(path), "--models", "0", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SATISFIABLE"
    assert payload["model_count"] == 2
    assert {tuple(model["atoms"]) for model in payload["models"]} == {
        ("selected(a)",),
        ("selected(b)",),
    }


def test_multiple_files_share_declarations(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    declarations = write_program(tmp_path, "#nherb status/1.\n", "declarations.aspf")
    rules = write_program(tmp_path, "status(alice) #= employed.\n", "rules.aspf")

    assert main([str(declarations), str(rules)]) == 0
    assert "status(alice)#=employed" in capsys.readouterr().out


def test_unsupported_diagnostic_includes_file_line_and_column(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    path = write_program(
        tmp_path,
        "#nherb balance/1.\nok :- balance(a) #>= 1.\n",
        "bad.aspf",
    )

    assert main([str(path)]) == 2
    error = capsys.readouterr().err
    assert f"{path}:2:" in error
    assert "#>=" in error


@pytest.mark.parametrize(
    ("source", "message", "column"),
    [
        ("ordinary.\n__aspf_injected(a).\n", "reserved for aspf-next internals", 1),
        (
            "#nherb balance/1.\np(balance(account1)).\n",
            "may only be used as the key of a supported n-atom",
            3,
        ),
    ],
)
def test_cli_rejects_semantic_boundary_violations_with_location(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
    source: str,
    message: str,
    column: int,
) -> None:
    path = write_program(tmp_path, source, "boundary.aspf")

    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:2:{column}" in captured.err
    assert message in captured.err
