from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_compatibility_report_is_derived_from_manifest() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/compatibility_report.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Historical Clingo{f} compatibility matrix" in result.stdout
    assert "baseline matching cases: 10" in result.stdout
    assert "passing:                35" in result.stdout
    assert "with restriction:" in result.stdout
    assert "invalid-and-rejected: 2" in result.stdout
    assert "expected unsupported:   4" in result.stdout
    assert "intentionally deferred: 4" in result.stdout
    assert "unresolved:             0" in result.stdout
    assert "total target cases:     39" in result.stdout
