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


@pytest.mark.parametrize(
    ("operator", "assigned", "right"),
    [("#<", -1, 0), ("#<=", 0, 0), ("#>", 1, 0), ("#>=", 0, 0)],
)
def test_ordered_comparisons_work_across_multiple_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    operator: str,
    assigned: int,
    right: int,
) -> None:
    declarations = write_program(tmp_path, "#nherb value/0.\n", "declarations.aspf")
    rules = write_program(
        tmp_path,
        f"value #= {assigned}.\nokay :- value {operator} {right}.\n",
        "rules.aspf",
    )

    assert main([str(declarations), str(rules)]) == 0
    assert "okay" in capsys.readouterr().out


def test_ordered_comparison_human_json_and_lowered_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_program(
        tmp_path,
        "#nherb balance/1.\nbalance(a) #= 2.\nok :- balance(a) #>= 1.\n",
        "ordered.aspf",
    )

    assert main([str(path)]) == 0
    human = capsys.readouterr().out
    assert "ok balance(a)#=2" in human
    assert "__aspf_" not in human

    assert main([str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["models"][0]["ordinary_atoms"] == ["ok"]
    assert payload["models"][0]["assignments"] == ["balance(a)#=2"]

    assert main([str(path), "--emit-lowered"]) == 0
    lowered = capsys.readouterr().out
    assert "__aspf_integer(2)." in lowered
    assert "_AspfCmp0 >= 1" in lowered


@pytest.mark.parametrize(
    "source",
    [
        "#nherb value/0.\nokay :- value #< 0.\n",
        "#nherb value/0.\nvalue #= symbolic.\nokay :- value #>= 0.\n",
    ],
)
def test_false_ordered_comparisons_do_not_leak_internal_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    path = write_program(tmp_path, source, "quiet.aspf")

    assert main([str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "__aspf_" not in captured.out


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
def test_cli_rejects_ordered_comparison_rule_head_with_location(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    operator: str,
) -> None:
    path = write_program(
        tmp_path,
        f"#nherb balance/1.\nbalance(a) {operator} 1.\n",
        "ordered-head.aspf",
    )

    assert main([str(path)]) == 2
    error = capsys.readouterr().err
    assert f"{path}:2:12" in error
    assert f"operator '{operator}'" in error


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


def test_domain_safe_variable_human_json_and_lowered_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_program(
        tmp_path,
        "#nherb balance/1.\naccount(a;b).\nbalance(a) #= 500.\n"
        "low(A) :- account(A), balance(A) #< 1000.\n",
        "variables.aspf",
    )

    assert main([str(path)]) == 0
    human = capsys.readouterr().out
    assert "account(a) account(b) low(a) balance(a)#=500" in human
    assert "__aspf_" not in human

    assert main([str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["models"][0]["ordinary_atoms"] == ["account(a)", "account(b)", "low(a)"]
    assert payload["models"][0]["assignments"] == ["balance(a)#=500"]

    assert main([str(path), "--emit-lowered"]) == 0
    lowered = capsys.readouterr().out
    assert "__aspf_value(balance(A),_AspfCmp0)" in lowered
    assert "__aspf_integer(_AspfCmp0)" in lowered


def test_domain_safe_variables_work_across_multiple_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    declarations = write_program(tmp_path, "#nherb status/1.\n", "declarations.aspf")
    rules = write_program(
        tmp_path,
        "person(alice;bob).\nstatus(P) #= active :- person(P).\n",
        "rules.aspf",
    )

    assert main([str(declarations), str(rules)]) == 0
    output = capsys.readouterr().out
    assert "status(alice)#=active" in output
    assert "status(bob)#=active" in output


def test_cli_rejects_unsafe_n_atom_variable_before_clingo_grounding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = "#nherb balance/1.\ndifferent(A) :- balance(A) #!= 1000.\n"
    path = write_program(tmp_path, source, "unsafe-variable.aspf")

    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    expected_column = source.splitlines()[1].index("balance(A)") + len("balance(") + 1
    assert captured.out == ""
    assert f"{path}:2:{expected_column}" in captured.err
    assert "ordinary positive body atom" in captured.err
