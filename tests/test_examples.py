from __future__ import annotations

from pathlib import Path

import pytest

from aspf_next.cli import main
from aspf_next.frontend import parse_program
from aspf_next.solver import SolveStatus, solve_program

PROJECT_ROOT = Path(__file__).parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


@pytest.mark.parametrize(
    ("filename", "status", "models", "expected_atoms"),
    [
        (
            "01_basic_assignment.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {("solvent(account1)", "balance(account1)#=500")},
        ),
        (
            "02_partial_function.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {
                (
                    "account(account1)",
                    "account(account2)",
                    "balance(account2)#=500",
                )
            },
        ),
        (
            "03_conditional_assignment.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {("active(alice)", "status(alice)#=employed")},
        ),
        ("04_conflicting_values.aspf", SolveStatus.UNSATISFIABLE, 0, set()),
        (
            "05_multiple_models.aspf",
            SolveStatus.SATISFIABLE,
            2,
            {("selected(blue)",), ("selected(red)",)},
        ),
        (
            "06_ordered_comparisons.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {
                (
                    "above_zero",
                    "at_least_twenty",
                    "at_most_zero",
                    "below_zero",
                    "temperature(freezer)#=-5",
                    "temperature(room)#=21",
                )
            },
        ),
        (
            "07_domain_safe_variables.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {
                (
                    "account(checking)",
                    "account(savings)",
                    "low(checking)",
                    "nonzero(checking)",
                    "nonzero(savings)",
                    "balance(checking)#=500",
                    "balance(savings)#=1500",
                )
            },
        ),
    ],
)
def test_documented_example(
    filename: str,
    status: SolveStatus,
    models: int,
    expected_atoms: set[tuple[str, ...]],
) -> None:
    path = EXAMPLES / filename
    program = parse_program(path.read_text(encoding="utf-8"), filename=str(path))
    result = solve_program(program, models=0)

    assert result.status is status
    assert len(result.models) == models
    assert {model.atoms for model in result.models} == expected_atoms


def test_examples_guide_covers_every_program() -> None:
    guide = (EXAMPLES / "README.md").read_text(encoding="utf-8")
    programs = sorted(EXAMPLES.glob("*.aspf"))

    assert len(programs) == 7
    for program in programs:
        assert program.name in guide


def test_readme_basic_command_output(capsys: pytest.CaptureFixture[str]) -> None:
    path = EXAMPLES / "01_basic_assignment.aspf"

    assert main([str(path)]) == 0
    assert capsys.readouterr().out == (
        "Answer: 1\nsolvent(account1) balance(account1)#=500\nSATISFIABLE\n"
    )


def test_quickstart_json_output_matches_cli(capsys: pytest.CaptureFixture[str]) -> None:
    path = EXAMPLES / "03_conditional_assignment.aspf"

    assert main([str(path), "--json"]) == 0
    output = capsys.readouterr().out.strip()
    quickstart = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    assert output in quickstart


@pytest.mark.parametrize("script", ["scripts/demo.sh", "scripts/demo.ps1"])
def test_demo_uses_verified_examples(script: str) -> None:
    content = (PROJECT_ROOT / script).read_text(encoding="utf-8")

    assert "examples/01_basic_assignment.aspf" in content
    assert "examples/04_conflicting_values.aspf" in content
