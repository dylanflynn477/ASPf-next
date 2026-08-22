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
    assert "docs/specification-traceability.md" in readme
    assert "docs/releases/not-equal-development.md" in readme
    assert "docs/releases/ordered-comparisons-development.md" in readme
    assert "docs/releases/domain-safe-variables-development.md" in readme
    assert "undefined" in readme and "#!=" in readme


def test_architecture_documents_required_pipeline_and_research_backend() -> None:
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
    assert "not production-wired" in architecture
    assert "PARTIAL GO" in architecture


def test_release_metadata_is_consistent() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert metadata["version"] == __version__ == "0.2.0a2"
    assert metadata["authors"] == [{"name": "Dylan Flynn"}]
    assert metadata["license"] == "PolyForm-Noncommercial-1.0.0"
    assert "License :: Other/Proprietary License" in metadata["classifiers"]
    assert not any("OSI Approved" in item for item in metadata["classifiers"])
    assert metadata["urls"]["Repository"] == "https://github.com/dylanflynn477/ASPf-next"
    assert "answer-set-programming" in metadata["keywords"]
    assert "Development Status :: 2 - Pre-Alpha" in metadata["classifiers"]

    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    portfolio = (PROJECT_ROOT / "docs" / "portfolio-copy.md").read_text(encoding="utf-8")
    assert "0.2.0a2 - Unreleased" in changelog
    assert "current source version is the unpublished `0.2.0a2`" in readme.lower()
    assert "Release candidate | `0.2.0a2`" in portfolio


def test_license_transition_is_explicit_and_nonretroactive() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    licensing = (PROJECT_ROOT / "docs" / "licensing.md").read_text(encoding="utf-8")

    assert license_text.startswith("# PolyForm Noncommercial License 1.0.0")
    assert "Required Notice: Copyright 2026 Dylan Flynn." in license_text
    assert "0.2.0a1` was released under the MIT License" in readme
    assert "does not revoke" in readme
    assert "other repository revision" in readme
    assert "not OSI-approved" in readme
    assert "not legal advice" in licensing
    assert "commercial evaluation" in licensing


def test_project_and_release_documents_exist() -> None:
    expected = (
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "PLAN.md",
        "docs/quickstart.md",
        "docs/roadmap.md",
        "docs/demo-recording.md",
        "docs/portfolio-copy.md",
        "docs/licensing.md",
        "docs/releases/0.2.0a1.md",
        "docs/releases/0.2.0a2.md",
        "docs/releases/not-equal-development.md",
        "docs/releases/ordered-comparisons-development.md",
        "docs/releases/domain-safe-variables-development.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
    )

    for relative_path in expected:
        assert (PROJECT_ROOT / relative_path).is_file(), relative_path


def test_conformance_traceability_and_decisions_cover_the_current_boundary() -> None:
    traceability = (PROJECT_ROOT / "docs" / "specification-traceability.md").read_text(
        encoding="utf-8"
    )
    for construct in (
        "Explicit declaration",
        "Partial function assignment",
        "Functionality",
        "Undefined applications",
        "Assignment fact",
        "Assignment rule head",
        "Positive body equality",
        "Positive body inequality",
        "Positive body ordered comparison",
        "Constants and values",
        "Ordinary ASP interaction",
        "Variables and arithmetic",
        "Declaration scope",
        "Reserved internal identifiers",
    ):
        assert f"| {construct} |" in traceability


def test_historical_compatibility_documents_and_manifest_are_linked() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "docs" / "compatibility" / "policy.md").read_text(encoding="utf-8")
    audit = (PROJECT_ROOT / "docs" / "compatibility" / "historical-clingof-audit.md").read_text(
        encoding="utf-8"
    )

    assert "Historical Clingo{f} compatibility" in readme
    assert "does not claim full" in readme
    assert "Source compatible" in policy and "Semantically compatible" in policy
    assert "Default-negated n-atoms" in audit
    assert "tests/historical_compat" in readme

    decision_files = sorted((PROJECT_ROOT / "docs" / "decisions").glob("*.md"))
    assert [path.name for path in decision_files] == [
        "0001-clean-room-implementation.md",
        "0002-reference-lowering-before-native-backend.md",
        "0003-partial-not-total-functions.md",
        "0004-conservative-unsupported-syntax.md",
        "0005-reserved-backend-namespace.md",
    ]
    for decision_file in decision_files:
        decision = decision_file.read_text(encoding="utf-8")
        assert "Status: Accepted" in decision
        assert "## Context" in decision
        assert "## Decision" in decision
        assert "## Consequences" in decision


def test_not_equal_documentation_records_the_semantic_boundary() -> None:
    required_documents = (
        "README.md",
        "docs/supported-language.md",
        "docs/compatibility-matrix.md",
        "docs/quickstart.md",
        "docs/roadmap.md",
        "CHANGELOG.md",
        "docs/releases/not-equal-development.md",
    )

    for relative_path in required_documents:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "#!=" in content, relative_path

    supported = (PROJECT_ROOT / "docs" / "supported-language.md").read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "docs" / "releases" / "not-equal-development.md").read_text(
        encoding="utf-8"
    )
    assert "undefined application makes the literal false" in " ".join(supported.split())
    assert "not __aspf_value" in development
    assert "Included in `0.2.0a1`" in development


def test_ordered_comparison_documentation_records_numeric_boundary() -> None:
    required_documents = (
        "README.md",
        "docs/supported-language.md",
        "docs/compatibility-matrix.md",
        "docs/quickstart.md",
        "docs/roadmap.md",
        "CHANGELOG.md",
        "docs/releases/ordered-comparisons-development.md",
    )

    for relative_path in required_documents:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "#<" in content and "#>=" in content, relative_path

    development = (
        PROJECT_ROOT / "docs" / "releases" / "ordered-comparisons-development.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(development.split())
    assert "defined integer value" in normalized
    assert "No coercion is performed" in normalized
    assert "Included in `0.2.0a1`" in development


def test_variable_documentation_records_the_source_safety_boundary() -> None:
    required_documents = (
        "README.md",
        "docs/supported-language.md",
        "docs/compatibility-matrix.md",
        "docs/quickstart.md",
        "docs/roadmap.md",
        "docs/semantics-notes.md",
        "CHANGELOG.md",
        "docs/releases/domain-safe-variables-development.md",
    )

    for relative_path in required_documents:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        normalized = " ".join(content.split())
        assert "domain-safe" in normalized.lower(), relative_path

    development = (
        PROJECT_ROOT / "docs" / "releases" / "domain-safe-variables-development.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(development.split())
    assert "ordinary, unnegated positive symbolic body atom" in normalized
    assert "positive scalar seed equality" in normalized
    assert "Included in `0.2.0a1`" in development


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
