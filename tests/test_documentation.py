from __future__ import annotations

import re
import tomllib
from pathlib import Path

from aspf_next import __version__

PROJECT_ROOT = Path(__file__).parents[1]
MARKDOWN_TARGET = re.compile(r"\]\(([^)]+)\)")


def test_readme_contains_required_scope_and_attribution() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "independent clean-room modernization" in readme
    assert "Marcello Balduccini" in readme
    assert "Potassco" in readme and "flingo" in readme
    assert "reference translation" in readme
    assert "not a native" in readme
    assert "does not claim full" in readme
    assert "Try it in under two minutes" in readme
    assert "Status: pre-alpha" in readme
    assert "examples/01_basic_assignment.aspf" in readme


def test_architecture_documents_required_pipeline_and_future_backend() -> None:
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    for stage in (
        "legacy syntax",
        "Compatibility frontend",
        "Typed ASP{f} IR",
        "Reference lowering",
        "Clingo 5.8",
        "Normalized ASP{f}-style",
    ):
        assert stage in architecture
    assert "```mermaid" in architecture
    assert "stroke-dasharray" in architecture
    assert "theory atoms" in architecture
    assert "custom Python propagator" in architecture
    assert "not implemented" in architecture


def test_release_metadata_is_consistent() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert metadata["version"] == __version__ == "0.1.0a1"
    assert metadata["authors"] == [{"name": "Dylan Flynn"}]
    assert metadata["urls"]["Repository"] == "https://github.com/dylanflynn477/ASPf-next"
    assert "answer-set-programming" in metadata["keywords"]
    assert "Development Status :: 2 - Pre-Alpha" in metadata["classifiers"]


def test_productization_documents_exist() -> None:
    expected = (
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "PRODUCTIZATION_PLAN.md",
        "docs/quickstart.md",
        "docs/roadmap.md",
        "docs/demo-recording.md",
        "docs/portfolio-copy.md",
        "docs/releases/0.1.0-alpha.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
    )

    for relative_path in expected:
        assert (PROJECT_ROOT / relative_path).is_file(), relative_path


def test_relative_markdown_links_resolve() -> None:
    markdown_files = [
        *PROJECT_ROOT.glob("*.md"),
        *(PROJECT_ROOT / "docs").rglob("*.md"),
        PROJECT_ROOT / "examples" / "README.md",
    ]

    for document in markdown_files:
        content = document.read_text(encoding="utf-8")
        for target in MARKDOWN_TARGET.findall(content):
            if "://" in target or target.startswith("#"):
                continue
            path = target.split("#", maxsplit=1)[0]
            assert (document.parent / path).exists(), f"{document}: broken link to {target}"
