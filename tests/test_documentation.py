from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def test_readme_contains_required_scope_and_attribution() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "independent clean-room modernization" in readme
    assert "Marcello Balduccini" in readme
    assert "Potassco" in readme and "flingo" in readme
    assert "reference translation" in readme
    assert "not a native" in readme
    assert "does not claim full" in readme


def test_architecture_documents_required_pipeline_and_future_backend() -> None:
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    for stage in (
        "legacy syntax",
        "compatibility frontend",
        "ASP{f} IR",
        "reference lowering",
        "Clingo",
        "normalized model output",
    ):
        assert stage in architecture
    assert "theory atoms" in architecture
    assert "custom Python propagator" in architecture
    assert "not implemented" in architecture
