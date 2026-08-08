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
        (
            "08_application_comparisons.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {
                (
                    "above_expected(b)",
                    "account(a)",
                    "account(b)",
                    "account(c)",
                    "changed(b)",
                    "matches(a)",
                    "actual(a)#=100",
                    "actual(b)#=125",
                    "expected(a)#=100",
                    "expected(b)#=100",
                )
            },
        ),
        (
            "09_default_negation.aspf",
            SolveStatus.SATISFIABLE,
            1,
            {
                (
                    "account(a)",
                    "account(b)",
                    "account(c)",
                    "needs_review(a)",
                    "needs_review(c)",
                    "balance(a)#=500",
                    "balance(b)#=1500",
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

    assert len(programs) == 9
    for program in programs:
        assert program.name in guide


@pytest.mark.parametrize(
    ("filename", "expected_atoms"),
    [
        ("alternative-declaration.aspf", ("f(a)#=2",)),
        ("compound-herbrand-value.aspf", ("same", "f(a)#=k(1)")),
        ("ordinary-declared-symbol.aspf", ("ordinary(k(1))", "k(1)#=5")),
        ("multiple-arities.aspf", ("f(a)#=one", "f(a,b)#=two")),
    ],
)
def test_historical_example(filename: str, expected_atoms: tuple[str, ...]) -> None:
    path = EXAMPLES / "historical" / filename
    program = parse_program(path.read_text(encoding="utf-8"), filename=str(path))
    result = solve_program(program, models=0)

    assert result.status is SolveStatus.SATISFIABLE
    assert result.models[0].atoms == expected_atoms


def test_historical_examples_guide_covers_every_program() -> None:
    directory = EXAMPLES / "historical"
    guide = (directory / "README.md").read_text(encoding="utf-8")

    for program in sorted(directory.glob("*.aspf")):
        assert program.name in guide


def test_portfolio_demo_distinguishes_defined_zero_missing_data_and_threshold_failure() -> None:
    path = EXAMPLES / "portfolio" / "technical_indicators.aspf"
    program = parse_program(path.read_text(encoding="utf-8"), filename=str(path))
    result = solve_program(program, models=0)

    assert result.status is SolveStatus.SATISFIABLE
    assert len(result.models) == 1
    assert result.models[0].ordinary_atoms == (
        "above_average(15)",
        "needs_review(15)",
        "needs_review(16)",
        "zero_average(14)",
        "zero_average(16)",
    )
    assert result.models[0].assignments == (
        "confidence(14)#=80",
        "confidence(15)#=45",
        "sma14_delta(14)#=0",
        "sma14_delta(15)#=1",
        "sma14_delta(16)#=0",
    )
    assert all(
        not atom.startswith(("above_average(", "zero_average("))
        for day in range(1, 14)
        for atom in result.models[0].ordinary_atoms
        if atom.endswith(f"({day})")
    )


def test_portfolio_demo_documentation_is_reproducible_and_non_predictive() -> None:
    document = (PROJECT_ROOT / "docs" / "portfolio-demo.md").read_text(encoding="utf-8")

    assert "aspf examples/portfolio/technical_indicators.aspf --models 0" in document
    assert "undefined ≠ 0" in document
    assert "not an “is undefined” operator" in document
    assert "no buy/sell recommendation" in document


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
