from __future__ import annotations

import json
from pathlib import Path

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
